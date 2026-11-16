"""Voice layer (ADR 0002): the Speaker port, plan-to-audio rendering, speaker registry.

TTS backends run in their own environment (experiments/voices/README.md); the text MVP needs none of this."""

from __future__ import annotations

from nichd_sim.voice.audio import Audio
from nichd_sim.voice.kokoro_speaker import KokoroSpeaker, SpeakerError
from nichd_sim.voice.render import RenderedSpeech, Span, render_log, render_speech
from nichd_sim.voice.speaker import Speaker, ToneSpeaker

SPEAKERS = {
    "tone": ToneSpeaker,
    "kokoro": lambda: KokoroSpeaker(child=True),
    "kokoro-adulte": lambda: KokoroSpeaker(child=False),
}
"""Available speakers by name (`kokoro` = child voice; needs Kokoro's venv, see experiments/voices)."""


def default_speaker_name() -> str:
    """`kokoro` (child voice) when its environment is installed, else the model-free `tone`."""
    from nichd_sim.voice.kokoro_speaker import find_python

    try:
        find_python()
        return "kokoro"
    except SpeakerError:
        return "tone"


def make_speaker(name: str | None = None) -> Speaker:
    name = name or default_speaker_name()
    try:
        factory = SPEAKERS[name]
    except KeyError:
        raise ValueError(f"voix inconnue {name!r} (disponibles : {', '.join(sorted(SPEAKERS))})") from None
    return factory()


__all__ = [
    "SPEAKERS",
    "Audio",
    "KokoroSpeaker",
    "RenderedSpeech",
    "Span",
    "Speaker",
    "SpeakerError",
    "ToneSpeaker",
    "default_speaker_name",
    "make_speaker",
    "render_log",
    "render_speech",
]
