"""Qwen3-TTS speaker: drives `qwen_worker.py` in Qwen's venv over a pipe (voice v2).

Chosen by the v2 screening (docs/evaluations/voix-v2.md): a child voice designed from a text
description, cloned by Qwen3-TTS Base, naturalness 4.8/5 in blind listening against 1/5 for the
Kokoro voice. Apache-2.0, deterministic once seeded.

The voice bank (`nichd_sim/data/voices/`) holds one synthetic voice per gender × age band of the
engine; `voice_for(profile)` picks the child's. The reply is said in one go (`native`): the renderer
writes the pauses as « … » and re-times them to the engine's plan.
"""

from __future__ import annotations

import base64
import json
import zlib
from array import array
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from nichd_sim.voice.audio import Audio
from nichd_sim.voice.worker import VoiceError, WorkerProcess, find_python

if TYPE_CHECKING:
    from nichd_sim.scenario import ChildProfile

WORKER = Path(__file__).with_name("qwen_worker.py")
ENV_VAR = "NICHD_QWEN_PYTHON"
ENV_DIR = Path("experiments/voices/.envs/qwen")
BANK = Path(__file__).resolve().parents[1] / "data" / "voices"
DEFAULT_VOICE = "fille_7_9"


@cache
def voice_bank() -> dict[str, dict]:
    """Voice id → {file, ref_text, gender, band, instruct}."""
    return json.loads((BANK / "voices.json").read_text(encoding="utf-8"))


def voice_for(profile: ChildProfile | None) -> str:
    """The bank voice matching the child's voice (girl / boy) and age band; girl 7–9 by default."""
    if profile is None:
        return DEFAULT_VOICE
    gender = profile.voice.value if profile.voice else "fille"
    vid = f"{gender}_{profile.age_band.value}"
    return vid if vid in voice_bank() else DEFAULT_VOICE


class QwenSpeaker:
    sample_rate = 24000
    native = True
    """Says the whole reply in one go (pauses written « … »): render_speech uses the native style."""

    def __init__(self, voice: str = DEFAULT_VOICE, *, python: str | Path | None = None,
                 command: list[str] | None = None, share_with: QwenSpeaker | None = None):
        """`command` overrides the worker command line (tests); `share_with` reuses another
        speaker's worker (one model in GPU memory for several voices)."""
        if voice not in voice_bank():
            raise VoiceError(f"voix inconnue {voice!r} (banque : {', '.join(sorted(voice_bank()))})")
        self.voice = voice
        entry = voice_bank()[voice]
        self._ref = {"ref_audio": str(BANK / entry["file"]), "ref_text": entry["ref_text"]}
        if share_with is not None:
            self._worker = share_with._worker
        else:
            # -I: isolated mode, the worker never imports files sitting next to it
            command = command or [str(python or find_python(ENV_VAR, ENV_DIR)), "-I", str(WORKER)]
            self._worker = WorkerProcess(command, name="Qwen3-TTS")

    def synthesize(self, text: str, *, rate: float = 1.0) -> Audio:
        """Seeded by the voice and the text: the same reply always sounds the same (replayable audio)."""
        seed = zlib.crc32(f"{self.voice}\x1f{text}".encode())
        resp = self._worker.request({"text": text, "rate": rate, "seed": seed, **self._ref})
        self.sample_rate = resp["sample_rate"]
        samples = array("h")
        samples.frombytes(base64.b64decode(resp["audio"]))
        return Audio(self.sample_rate, samples)

    def close(self) -> None:
        self._worker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:  # noqa: BLE001, S110 — best effort at interpreter shutdown
            pass
