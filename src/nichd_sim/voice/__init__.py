"""Voice layer (ADR 0002): the Speaker port, plan-to-audio rendering, speaker registry.

TTS backends run in their own environment (experiments/voices/README.md); the text MVP needs none of this."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nichd_sim.voice.audio import Audio
from nichd_sim.voice.kokoro_speaker import KokoroSpeaker, SpeakerError
from nichd_sim.voice.qwen_speaker import QwenSpeaker, voice_bank, voice_for
from nichd_sim.voice.render import RenderedSpeech, Span, render_log, render_speech
from nichd_sim.voice.speaker import Speaker, ToneSpeaker
from nichd_sim.voice.worker import VoiceError

if TYPE_CHECKING:
    from nichd_sim.scenario import ChildProfile

SPEAKERS = {
    "tone": lambda child=None: ToneSpeaker(),
    "qwen": lambda child=None: QwenSpeaker(voice_for(child)),
    "kokoro": lambda child=None: KokoroSpeaker(child=True),
    "kokoro-adulte": lambda child=None: KokoroSpeaker(child=False),
}
"""Available speakers by name, each built for a child profile (or None).

`qwen` = the child's voice from the bank (gender × age band, voice v2), needs Qwen's venv;
`kokoro` = the former child voice, needs Kokoro's venv (experiments/voices/README.md)."""


def default_speaker_name() -> str:
    """`qwen` when its environment is installed, else `kokoro`, else the model-free `tone`."""
    from nichd_sim.voice import kokoro_speaker, qwen_speaker
    from nichd_sim.voice.worker import find_python

    for name, env_var, env_dir in (("qwen", qwen_speaker.ENV_VAR, qwen_speaker.ENV_DIR),
                                   ("kokoro", kokoro_speaker.ENV_VAR, None)):
        try:
            find_python(env_var, env_dir) if env_dir else find_python(env_var)
            return name
        except VoiceError:
            continue
    return "tone"


def make_speaker(name: str | None = None, child: ChildProfile | None = None) -> Speaker:
    """The named speaker (default: the best installed) for this child (`qwen` picks its voice)."""
    name = name or default_speaker_name()
    try:
        factory = SPEAKERS[name]
    except KeyError:
        raise ValueError(f"voix inconnue {name!r} (disponibles : {', '.join(sorted(SPEAKERS))})") from None
    return factory(child)


__all__ = [
    "SPEAKERS",
    "Audio",
    "KokoroSpeaker",
    "QwenSpeaker",
    "RenderedSpeech",
    "Span",
    "Speaker",
    "SpeakerError",
    "ToneSpeaker",
    "VoiceError",
    "default_speaker_name",
    "make_speaker",
    "render_log",
    "render_speech",
    "voice_bank",
    "voice_for",
]
