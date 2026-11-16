"""Kokoro speaker: drives `kokoro_worker.py` in the voice venv over a pipe.

Selected by the TTS screening (experiments/voices/results/report.md): ff_siwis voice with pitch and
formants × 1.25 (child, F0 ≈ 266 Hz), deterministic once seeded, 0.1 s per segment, 1 GB GPU.
"""

from __future__ import annotations

import base64
import zlib
from array import array
from pathlib import Path

from nichd_sim.voice.audio import Audio
from nichd_sim.voice.worker import VoiceError, WorkerProcess, find_python

WORKER = Path(__file__).with_name("kokoro_worker.py")
ENV_VAR = "NICHD_KOKORO_PYTHON"
CHILD_FACTOR = 1.25
DEFAULT_VOICE = "ff_siwis"

SpeakerError = VoiceError


class KokoroSpeaker:
    sample_rate = 24000

    def __init__(self, *, child: bool = True, voice: str = DEFAULT_VOICE, python: str | Path | None = None,
                 command: list[str] | None = None, share_with: KokoroSpeaker | None = None):
        """`command` overrides the worker command line (tests); `share_with` reuses another
        speaker's worker (one model in GPU memory for the child and the interviewer voices)."""
        self.factor = CHILD_FACTOR if child else 1.0
        self.voice = voice
        if share_with is not None:
            self._worker = share_with._worker
        else:
            # -I: isolated mode, the worker never imports files sitting next to it
            command = command or [str(python or find_python(ENV_VAR)), "-I", str(WORKER)]
            self._worker = WorkerProcess(command, name="Kokoro")

    def synthesize(self, text: str, *, rate: float = 1.0) -> Audio:
        return self.synthesize_pieces([text], rate=rate)[0]

    def synthesize_pieces(self, pieces: list[str], *, rate: float = 1.0) -> list[Audio]:
        """The pieces spoken as ONE utterance, returned cut at the piece boundaries.
        Seeded by the text, so the same reply always sounds the same (replayable audio)."""
        seed = zlib.crc32("\x1f".join(pieces).encode())
        resp = self._worker.request({"pieces": pieces, "rate": rate, "seed": seed, "voice": self.voice,
                                     "factor": self.factor})
        self.sample_rate = resp["sample_rate"]
        out = []
        for b64 in resp["pieces"]:
            samples = array("h")
            samples.frombytes(base64.b64decode(b64))
            out.append(Audio(self.sample_rate, samples))
        return out

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
