"""Speech plan → audio: TTS for the speech chunks, exact silences in between."""

from __future__ import annotations

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


def render_speech(plan: list[SpeechChunk], speaker: Speaker, delivery: Delivery | None = None) -> RenderedSpeech:
    rate = delivery.rate if delivery else 1.0
    gain = VOLUME_GAIN[delivery.volume] if delivery else 1.0
    audio = Audio(speaker.sample_rate)
    timeline: list[Span] = []
    for chunk in plan:
        start = audio.duration_ms
        if chunk.kind == ChunkKind.SILENCE:
            piece = Audio.silence(speaker.sample_rate, chunk.ms)
        else:
            piece = speaker.synthesize(chunk.text, rate=rate).trimmed().scaled(gain)
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
