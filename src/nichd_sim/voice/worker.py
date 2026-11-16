"""Worker processes: TTS / STT backends run in their own venv, driven over a pipe (JSON lines).

The voice venv (experiments/voices/README.md) holds torch, Kokoro and faster-whisper; the project venv
stays light. A worker is started on first request, reports its errors, and is restarted if it dies.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

VOICE_ENV = Path("experiments/voices/.envs/kokoro")
"""Default voice venv, relative to the repository root."""


class VoiceError(RuntimeError):
    pass


def find_python(env_var: str) -> Path:
    """Python of the voice venv: $<env_var>, else experiments/voices/.envs/kokoro."""
    if os.environ.get(env_var):
        return Path(os.environ[env_var])
    rel = VOICE_ENV / "bin" / "python"
    for root in (Path.cwd(), Path(__file__).resolve().parents[3]):
        if (root / rel).exists():
            return root / rel
    raise VoiceError(
        f"environnement voix introuvable : installez-le (experiments/voices/README.md) ou définissez {env_var}"
    )


def cuda_library_path(python: Path) -> str:
    """CUDA libraries shipped as wheels in the venv (cuBLAS, cuDNN), for CTranslate2 (faster-whisper)."""
    venv = Path(python).parent.parent
    dirs = sorted(str(d) for d in venv.glob("lib/python3*/site-packages/nvidia/*/lib"))
    return ":".join(dirs)


class WorkerProcess:
    def __init__(self, command: list[str], *, name: str, env: dict[str, str] | None = None):
        self.command = command
        self.name = name
        self.env = env
        self._proc: subprocess.Popen | None = None
        self._stderr = None

    def request(self, payload: dict) -> dict:
        proc = self._start()
        try:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
        except (BrokenPipeError, OSError) as e:
            raise VoiceError(f"le processus {self.name} s'est arrêté : {self._tail()}") from e
        if not line:
            raise VoiceError(f"le processus {self.name} s'est arrêté : {self._tail()}")
        resp = json.loads(line)
        if "error" in resp:
            raise VoiceError(f"{self.name} : {resp['error']}")
        return resp

    def _start(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            self._stderr = tempfile.TemporaryFile(mode="w+")  # noqa: SIM115 — lives as long as the worker
            env = {**os.environ, **self.env} if self.env else None
            self._proc = subprocess.Popen(
                self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                text=True, encoding="utf-8", bufsize=1, env=env,
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
