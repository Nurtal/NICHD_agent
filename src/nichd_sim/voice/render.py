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


def style_for(speaker: Speaker) -> RenderStyle:
    """A speaker that says the whole reply in one go (`native = True`, e.g. Qwen3-TTS) gets the native
    style with room tone; the others keep the original spliced assembly."""
    return NATIVE_STYLE if getattr(speaker, "native", False) else DEFAULT_STYLE


def render_speech(plan: list[SpeechChunk], speaker: Speaker, delivery: Delivery | None = None,
                  style: RenderStyle | None = None) -> RenderedSpeech:
    style = style or style_for(speaker)
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
    retimed = _retimed(plan, voice, onset, style)
    if retimed is not None:
        return retimed
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


PAD_MS = 40
"""Sound kept on each side of a measured speech stretch when the pauses are re-timed (soft onsets, decays)."""


def _retimed(plan, voice: Audio, onset: int, style: RenderStyle) -> RenderedSpeech | None:
    """The native voice with each of its pauses set to the planned length.

    The engine decides how long the child hesitates (ADR 0002); the TTS only decides how the words
    sound. The voice is cut in quiet stretches (keeping up to PAD_MS of sound on each side), one cut
    per planned pause, and the pieces are laid on the planned silences. The voice does not always pause
    where the text says « … »: it may pause at a comma too, or run « euh… non » together. So every
    quiet stretch of at least CUT_MIN_MS is a candidate, and each planned pause takes the candidate
    closest to where the text puts it (`_choose_cuts`). None when the voice has too few quiet
    stretches: the caller keeps the voice as spoken and measures its timeline."""
    speech = [c for c in plan if c.kind == ChunkKind.SPEECH]
    if len(speech) < 2:
        return None
    cuts = _choose_cuts(quiet_gaps(voice), [len(c.text.strip()) or 1 for c in speech], voice)
    if cuts is None:
        return None
    bounds = [0, *[x for g in cuts for x in g], voice.duration_ms]
    spans = [(bounds[2 * k], bounds[2 * k + 1]) for k in range(len(speech))]
    gaps, pending, seen = [], 0, False  # planned silence between consecutive speech chunks
    for c in plan:
        if c.kind == ChunkKind.SPEECH:
            if seen:
                gaps.append(pending)
            seen, pending = True, 0
        elif seen:
            pending += c.ms
    sr = voice.sample_rate
    n = len(spans)
    pads = [min(PAD_MS, (spans[k + 1][0] - spans[k][1]) // 2) for k in range(n - 1)]
    audio = Audio(sr)
    audio.extend(Audio.silence(sr, onset))
    timeline = [Span(ChunkKind.SILENCE, 0, onset)] if onset else []
    for k, ((a, b), chunk) in enumerate(zip(spans, speech)):
        pad_in = pads[k - 1] if k else 0
        pad_out = pads[k] if k < n - 1 else 0
        lo = 0 if k == 0 else _at(sr, a - pad_in)
        hi = len(voice.samples) if k == n - 1 else _at(sr, b + pad_out)
        piece = Audio(sr, voice.samples[lo:hi]).faded(style.fade_ms)  # cut in quiet parts: no click
        start = audio.duration_ms
        audio.extend(piece)
        timeline.append(Span(ChunkKind.SPEECH, start + pad_in, audio.duration_ms - pad_out, chunk.text))
        if k < n - 1:
            pause = max(gaps[k], pad_out + pads[k])
            audio.extend(Audio.silence(sr, pause - pad_out - pads[k]))
            timeline.append(Span(ChunkKind.SILENCE, audio.duration_ms - pause + pads[k], audio.duration_ms + pads[k]))
    return RenderedSpeech(audio, timeline)


CUT_MIN_MS = 30
"""Shortest quiet stretch where the voice may be cut to lay a planned pause."""
DIP_PENALTY = 0.1
"""Cost of cutting at an energy dip rather than in a real silence (in shares of the reply's length)."""
FILLER_CHARS = 8
"""A filler (« euh… ») lasts about as long as 8 written characters."""


def _frame_rms(audio: Audio, frame_ms: int = 10) -> list[float]:
    n = max(1, round(audio.sample_rate * frame_ms / 1000))
    s = audio.samples
    return [(sum(x * x for x in s[i : i + n]) / len(s[i : i + n])) ** 0.5 for i in range(0, len(s), n)]


def energy_dips(audio: Audio, around_ms: list[float], window_ms: int = 250, frame_ms: int = 10,
                rel: float = 0.25) -> list[tuple[int, int]]:
    """Where the voice runs two pieces together (« euh… non » without a pause): the weakest frame
    near each expected boundary, as a zero-length cut — if it is clearly weaker than the voice."""
    rms = _frame_rms(audio, frame_ms)
    if not rms or max(rms) == 0:
        return []
    dips = []
    for t in around_ms:
        lo, hi = max(1, int((t - window_ms) // frame_ms)), min(len(rms) - 1, int((t + window_ms) // frame_ms))
        if hi <= lo:
            continue
        k = min(range(lo, hi), key=lambda i: rms[i])
        if rms[k] < rel * max(rms):
            dips.append((k * frame_ms, k * frame_ms + frame_ms))
    return dips


def quiet_gaps(audio: Audio, min_ms: int = CUT_MIN_MS, frame_ms: int = 10, rel: float = 0.06) -> list[tuple[int, int]]:
    """Quiet stretches (start_ms, end_ms) of at least `min_ms` between the first and the last sound."""
    rms = _frame_rms(audio, frame_ms)
    if not rms or max(rms) == 0:
        return []
    loud = [r >= rel * max(rms) for r in rms]
    first = loud.index(True)
    last = len(loud) - 1 - loud[::-1].index(True)
    gaps, start = [], None
    for k in range(first, last + 1):
        if not loud[k] and start is None:
            start = k
        elif loud[k] and start is not None:
            if (k - start) * frame_ms >= min_ms:
                gaps.append((start * frame_ms, k * frame_ms))
            start = None
    return gaps


def _choose_cuts(gaps: list[tuple[int, int]], weights: list[int], voice: Audio) -> list[tuple[int, int]] | None:
    """One quiet stretch per boundary between speech pieces, in order: the boundary written after
    piece k is expected at the share of the text said so far; each boundary takes the gap closest to
    it, longer gaps preferred (dynamic programming over the gaps, monotonic)."""
    m = len(weights) - 1
    w = [FILLER_CHARS if x <= 4 else x for x in weights]
    total = voice.duration_ms
    expected = [total * sum(w[: k + 1]) / sum(w) for k in range(m)]
    # The voice may run two pieces together (« euh je sais pas »): the energy dips near the expected
    # boundaries are candidates too, slightly penalized, so that a dip where the text puts the pause
    # beats a real silence far from it (a breath at the end of the reply).
    dips = set(energy_dips(voice, expected)) - set(gaps)
    gaps = sorted(set(gaps) | dips)
    if len(gaps) < m:
        return None

    def cost(k: int, g: tuple[int, int]) -> float:
        mid = (g[0] + g[1]) / 2
        return abs(mid - expected[k]) / total - 0.15 * min(g[1] - g[0], 300) / 300 + (DIP_PENALTY if g in dips else 0)

    inf = float("inf")
    best = [[inf] * len(gaps) for _ in range(m)]  # best[k][j]: boundary k at gap j
    back = [[-1] * len(gaps) for _ in range(m)]
    for j, g in enumerate(gaps):
        best[0][j] = cost(0, g)
    for k in range(1, m):
        run, arg = inf, -1
        for j, g in enumerate(gaps):
            if j and best[k - 1][j - 1] < run:
                run, arg = best[k - 1][j - 1], j - 1
            if arg >= 0:
                best[k][j], back[k][j] = run + cost(k, g), arg
    j = min(range(len(gaps)), key=lambda j: best[m - 1][j])
    if best[m - 1][j] == inf:
        return None
    chosen = [j]
    for k in range(m - 1, 0, -1):
        j = back[k][j]
        chosen.append(j)
    return [gaps[j] for j in reversed(chosen)]


def _at(sample_rate: int, ms: int) -> int:
    return max(0, round(sample_rate * ms / 1000))


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
