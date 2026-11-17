"""Speech plan → audio: TTS for the speech chunks, exact silences in between."""

from __future__ import annotations

import random
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from nichd_sim.delivery import ChunkKind, Delivery, SpeechChunk, Volume, plan_speech
from nichd_sim.voice.audio import Audio
from nichd_sim.voice.speaker import Speaker

if TYPE_CHECKING:
    from nichd_sim.session import SessionLog

VOLUME_GAIN = {Volume.NORMAL: 1.0, Volume.LOW: 0.6, Volume.WHISPER: 0.35}


@dataclass(frozen=True)
class RenderStyle:
    """How the speech plan is assembled (voice screening v2). The default is the original assembly."""

    room_tone_db: float | None = None
    """Level (dBFS) of a quiet room-tone bed under the whole reply; None = digital silence."""
    fade_ms: int = 8
    """Fade at each cut point."""
    native: bool = False
    """Synthesize the whole reply in one go, pauses and fillers written in the text (« … », « euh… »);
    only the onset silence is imposed, and the timeline is measured on the audio."""


DEFAULT_STYLE = RenderStyle()
NATURAL_STYLE = RenderStyle(room_tone_db=-58.0, fade_ms=30)
NATIVE_STYLE = RenderStyle(room_tone_db=-58.0, fade_ms=30, native=True)
PAUSE_MARK = "…"
MIN_PAUSE_MS = 180
"""Shortest quiet stretch counted as a pause when measuring a natively rendered reply."""


def room_tone(sample_rate: int, ms: int, db: float, seed: int = 0) -> Audio:
    """Deterministic pink-ish noise at `db` dBFS (sum of three filtered noise layers)."""
    rng = random.Random(seed)
    n = round(sample_rate * ms / 1000)
    amp = 32767 * 10 ** (db / 20)
    b0 = b1 = b2 = 0.0
    out = array("h")
    for _ in range(n):
        w = rng.uniform(-1.0, 1.0)
        b0 = 0.99765 * b0 + w * 0.0990460
        b1 = 0.96300 * b1 + w * 0.2965164
        b2 = 0.57000 * b2 + w * 1.0526913
        out.append(int(max(-32767, min(32767, amp * 0.6 * (b0 + b1 + b2 + w * 0.1848)))))
    return Audio(sample_rate, out)


def native_text(plan: list[SpeechChunk]) -> str:
    """The reply as one text for a native rendering: inner silences become « … »."""
    parts: list[str] = []
    for i, c in enumerate(plan):
        if c.kind == ChunkKind.SPEECH:
            parts.append(c.text)
        elif i > 0 and parts and not parts[-1].endswith(PAUSE_MARK):
            parts[-1] = parts[-1].rstrip(" ,.") + PAUSE_MARK
    return " ".join(p.strip() for p in parts if p.strip())


def speech_spans(audio: Audio, start_ms: int = 0, frame_ms: int = 20) -> list[tuple[int, int]]:
    """Speech stretches of a reply, split at quiet stretches of at least MIN_PAUSE_MS."""
    bounds = audio.voiced_bounds(frame_ms=frame_ms)
    if bounds is None:
        return []
    n = max(1, round(audio.sample_rate * frame_ms / 1000))
    rms = []
    for i in range(0, len(audio.samples), n):
        frame = audio.samples[i : i + n]
        rms.append((sum(x * x for x in frame) / len(frame)) ** 0.5 if frame else 0.0)
    quiet = 0.08 * max(rms)
    spans, cur, gap = [], None, 0
    for k in range(bounds[0] // frame_ms, min(len(rms), bounds[1] // frame_ms)):
        if rms[k] >= quiet:
            if cur is None:
                cur = k
            gap = 0
        elif cur is not None:
            gap += 1
            if gap * frame_ms >= MIN_PAUSE_MS:
                spans.append((cur, k - gap + 1))
                cur, gap = None, 0
    if cur is not None:
        spans.append((cur, min(len(rms), bounds[1] // frame_ms)))
    return [(start_ms + a * frame_ms, start_ms + b * frame_ms) for a, b in spans if b > a]


@dataclass(frozen=True)
class Span:
    kind: ChunkKind
    start_ms: int
    end_ms: int
    text: str = ""


@dataclass
class RenderedSpeech:
    audio: Audio
    timeline: list[Span] = field(default_factory=list)
    """Where each chunk landed in the audio (for display, and later turn-taking metrics)."""

    @property
    def onset_ms(self) -> int:
        """Silence before the first speech: the child's response latency."""
        first = next((s for s in self.timeline if s.kind == ChunkKind.SPEECH), None)
        return first.start_ms if first else self.audio.duration_ms


def render_speech(plan: list[SpeechChunk], speaker: Speaker, delivery: Delivery | None = None,
                  style: RenderStyle = DEFAULT_STYLE) -> RenderedSpeech:
    if style.native:
        rendered = _render_native(plan, speaker, delivery, style)
    else:
        rendered = _render_spliced(plan, speaker, delivery, style)
    if style.room_tone_db is not None and rendered.audio.samples:
        rendered.audio.mix_at(room_tone(rendered.audio.sample_rate, rendered.audio.duration_ms, style.room_tone_db), 0)
    return rendered


def _render_native(plan, speaker, delivery, style) -> RenderedSpeech:
    rate = delivery.rate if delivery else 1.0
    gain = VOLUME_GAIN[delivery.volume] if delivery else 1.0
    onset = plan[0].ms if plan and plan[0].kind == ChunkKind.SILENCE else 0
    text = native_text(plan)
    audio = Audio(speaker.sample_rate)
    if not text:
        audio.extend(Audio.silence(audio.sample_rate, onset))
        return RenderedSpeech(audio, [Span(ChunkKind.SILENCE, 0, audio.duration_ms)])
    voice = speaker.synthesize(text, rate=rate).trimmed().faded(style.fade_ms).scaled(gain)
    audio = Audio(voice.sample_rate)
    audio.extend(Audio.silence(audio.sample_rate, onset))
    audio.extend(voice)
    spans = speech_spans(voice, start_ms=onset) or [(onset, audio.duration_ms)]
    spans[0] = (onset, spans[0][1])  # the voice was trimmed: it starts right after the imposed onset
    pieces = [p.strip() for p in text.split(PAUSE_MARK)]
    pieces = [p for p in pieces if p]
    texts = pieces if len(pieces) == len(spans) else [text] + [""] * (len(spans) - 1)
    timeline, t = [], 0
    for (a, b), piece in zip(spans, texts):
        if a > t:
            timeline.append(Span(ChunkKind.SILENCE, t, a))
        timeline.append(Span(ChunkKind.SPEECH, a, b, piece))
        t = b
    if t < audio.duration_ms:
        timeline.append(Span(ChunkKind.SILENCE, t, audio.duration_ms))
    return RenderedSpeech(audio, timeline)


def _render_spliced(plan, speaker, delivery, style) -> RenderedSpeech:
    rate = delivery.rate if delivery else 1.0
    gain = VOLUME_GAIN[delivery.volume] if delivery else 1.0
    texts = [c.text for c in plan if c.kind == ChunkKind.SPEECH]
    if hasattr(speaker, "synthesize_pieces") and texts:
        # One utterance cut at the pause points: continuous intonation, fillers in context.
        spoken = iter(speaker.synthesize_pieces(texts, rate=rate))
    else:
        spoken = iter(speaker.synthesize(t, rate=rate) for t in texts)
    audio = Audio(speaker.sample_rate)
    timeline: list[Span] = []
    for chunk in plan:
        start = audio.duration_ms
        if chunk.kind == ChunkKind.SILENCE:
            piece = Audio.silence(audio.sample_rate, chunk.ms)
        else:
            piece = next(spoken).trimmed().faded(style.fade_ms).scaled(gain)
            if not audio.samples and piece.sample_rate != audio.sample_rate:
                audio = Audio(piece.sample_rate)  # the speaker reports its real rate on first use
        audio.extend(piece)
        timeline.append(Span(chunk.kind, start, audio.duration_ms, chunk.text))
    return RenderedSpeech(audio, timeline)


def render_log(log: SessionLog, speaker: Speaker, out_dir: str | Path) -> list[Path]:
    """One WAV per child reply of a session log (any format: format 1 logs have no delivery)."""
    out = Path(out_dir)
    paths = []
    for t in log.turns:
        plan = plan_speech(t.response, t.decision.delivery)
        rendered = render_speech(plan, speaker, t.decision.delivery)
        paths.append(rendered.audio.write_wav(out / f"turn_{t.index:03d}.wav"))
    return paths
