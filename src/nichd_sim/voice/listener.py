"""Listener port (STT) and the faster-whisper listener."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from nichd_sim.voice.audio import Audio
from nichd_sim.voice.worker import WorkerProcess, cuda_library_path, find_python

WORKER = Path(__file__).with_name("whisper_worker.py")
ENV_VAR = "NICHD_WHISPER_PYTHON"
DEFAULT_MODEL = "large-v3"


@dataclass(frozen=True)
class Word:
    text: str
    start_ms: int
    end_ms: int


@dataclass
class Transcript:
    text: str
    words: list[Word] = field(default_factory=list)

    @property
    def speech_start_ms(self) -> int | None:
        """When the speaker actually started talking in the audio (leading silence excluded)."""
        return self.words[0].start_ms if self.words else None

    @property
    def speech_end_ms(self) -> int | None:
        return self.words[-1].end_ms if self.words else None


class Listener(Protocol):
    def transcribe(self, audio: Audio, *, prompt: str | None = None) -> Transcript:
        """French speech to text, with word timings. `prompt`: optional context (names…)."""
        ...


class WhisperListener:
    """faster-whisper large-v3 in the voice venv (already used as the TTS judge)."""

    def __init__(self, *, model: str = DEFAULT_MODEL, python: str | Path | None = None,
                 command: list[str] | None = None):
        self.model = model
        if command is None:
            py = Path(python or find_python(ENV_VAR))
            command, env = [str(py), "-I", str(WORKER)], {"LD_LIBRARY_PATH": cuda_library_path(py)}
        else:
            env = None
        self._worker = WorkerProcess(command, name="Whisper", env=env)

    def transcribe(self, audio: Audio, *, prompt: str | None = None) -> Transcript:
        resp = self._worker.request({
            "pcm": base64.b64encode(audio.samples.tobytes()).decode(),
            "sample_rate": audio.sample_rate, "prompt": prompt, "model": self.model,
        })
        return Transcript(resp["text"], [Word(w, s, e) for w, s, e in resp["words"]])

    def close(self) -> None:
        self._worker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()
