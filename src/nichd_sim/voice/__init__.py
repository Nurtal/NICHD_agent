"""Voice layer (ADR 0002): the Speaker port, plan-to-audio rendering, speaker registry.

Heavy TTS backends are optional (`uv sync --extra voice`); the text MVP needs none of this."""

from __future__ import annotations

from nichd_sim.voice.audio import Audio
from nichd_sim.voice.render import RenderedSpeech, Span, render_log, render_speech
from nichd_sim.voice.speaker import Speaker, ToneSpeaker

SPEAKERS = {"tone": ToneSpeaker}
"""Available speakers by name. TTS adapters register here once their backend is chosen."""


def make_speaker(name: str) -> Speaker:
    try:
        return SPEAKERS[name]()
    except KeyError:
        raise ValueError(f"voix inconnue {name!r} (disponibles : {', '.join(sorted(SPEAKERS))})") from None


__all__ = [
    "SPEAKERS",
    "Audio",
    "RenderedSpeech",
    "Span",
    "Speaker",
    "ToneSpeaker",
    "make_speaker",
    "render_log",
    "render_speech",
]
