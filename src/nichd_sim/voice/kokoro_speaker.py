"""Kokoro speaker: drives `kokoro_worker.py` in Kokoro's own venv over a pipe.

Kokoro and its torch build live in a separate environment (experiments/voices/README.md), so the
project venv stays light. The worker is started on first use and kept alive.

Selected by the TTS screening (experiments/voices/results/report.md): ff_siwis voice with pitch and
formants × 1.25 (child, F0 ≈ 266 Hz), deterministic once seeded, 0.1 s per segment, 1 GB GPU.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import zlib
from array import array
from pathlib import Path

from nichd_sim.voice.audio import Audio

WORKER = Path(__file__).with_name("kokoro_worker.py")
ENV_VAR = "NICHD_KOKORO_PYTHON"
CHILD_FACTOR = 1.25
DEFAULT_VOICE = "ff_siwis"


class SpeakerError(RuntimeError):
    pass


def find_python() -> Path:
    """Python of Kokoro's venv: $NICHD_KOKORO_PYTHON, else experiments/voices/.envs/kokoro."""
    if os.environ.get(ENV_VAR):
        return Path(os.environ[ENV_VAR])
    rel = Path("experiments/voices/.envs/kokoro/bin/python")
    for root in (Path.cwd(), Path(__file__).resolve().parents[3]):
        if (root / rel).exists():
            return root / rel
    raise SpeakerError(
        f"environnement Kokoro introuvable : installez-le (experiments/voices/README.md) ou définissez {ENV_VAR}"
    )


class KokoroSpeaker:
    sample_rate = 24000

    def __init__(self, *, child: bool = True, voice: str = DEFAULT_VOICE, python: str | Path | None = None,
                 command: list[str] | None = None):
        """`command` overrides the worker command line (tests)."""
        self.factor = CHILD_FACTOR if child else 1.0
        self.voice = voice
        # -I: isolated mode, the worker never imports files sitting next to it
        self._command = command or [str(python or find_python()), "-I", str(WORKER)]
        self._proc: subprocess.Popen | None = None
        self._stderr = None

    # -- Speaker port --------------------------------------------------------

    def synthesize(self, text: str, *, rate: float = 1.0) -> Audio:
        return self.synthesize_pieces([text], rate=rate)[0]

    def synthesize_pieces(self, pieces: list[str], *, rate: float = 1.0) -> list[Audio]:
        """The pieces spoken as ONE utterance, returned cut at the piece boundaries.
        Seeded by the text, so the same reply always sounds the same (replayable audio)."""
        seed = zlib.crc32("\x1f".join(pieces).encode())
        resp = self._request({"pieces": pieces, "rate": rate, "seed": seed, "voice": self.voice,
                              "factor": self.factor})
        self.sample_rate = resp["sample_rate"]
        out = []
        for b64 in resp["pieces"]:
            samples = array("h")
            samples.frombytes(base64.b64decode(b64))
            out.append(Audio(self.sample_rate, samples))
        return out

    # -- worker --------------------------------------------------------------

    def _request(self, payload: dict) -> dict:
        proc = self._start()
        try:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
        except (BrokenPipeError, OSError) as e:
            raise SpeakerError(f"le processus Kokoro s'est arrêté : {self._tail()}") from e
        if not line:
            raise SpeakerError(f"le processus Kokoro s'est arrêté : {self._tail()}")
        resp = json.loads(line)
        if "error" in resp:
            raise SpeakerError(f"Kokoro : {resp['error']}")
        return resp

    def _start(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            self._stderr = tempfile.TemporaryFile(mode="w+")
            self._proc = subprocess.Popen(
                self._command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                text=True, encoding="utf-8", bufsize=1,
            )
        return self._proc

    def _tail(self) -> str:
        if self._stderr is None:
            return ""
        self._stderr.seek(0)
        return " | ".join(self._stderr.read().strip().splitlines()[-3:])

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def __enter__(self) -> KokoroSpeaker:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
