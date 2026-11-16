"""Minimal mono 16-bit PCM audio, standard library only (no numpy in the text MVP)."""

from __future__ import annotations

import wave
from array import array
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Audio:
    sample_rate: int
    samples: array = field(default_factory=lambda: array("h"))
    """Signed 16-bit mono samples."""

    @property
    def duration_ms(self) -> int:
        return round(len(self.samples) * 1000 / self.sample_rate)

    @classmethod
    def silence(cls, sample_rate: int, ms: int) -> Audio:
        return cls(sample_rate, array("h", bytes(2 * round(sample_rate * ms / 1000))))

    def extend(self, other: Audio) -> None:
        if other.sample_rate != self.sample_rate:
            raise ValueError(f"fréquences d'échantillonnage différentes : {other.sample_rate} ≠ {self.sample_rate}")
        self.samples.extend(other.samples)

    def scaled(self, gain: float) -> Audio:
        if gain == 1.0:
            return self
        return Audio(self.sample_rate, array("h", (max(-32768, min(32767, int(s * gain))) for s in self.samples)))

    def trimmed(self, threshold: int = 300, margin_ms: int = 20) -> Audio:
        """Without leading/trailing near-silence (TTS padding), keeping a small margin.
        Keeps the planned silences exact: only the plan decides how long the child is silent."""
        loud = [i for i, s in enumerate(self.samples) if abs(s) > threshold]
        if not loud:
            return Audio(self.sample_rate)
        margin = round(self.sample_rate * margin_ms / 1000)
        start, end = max(0, loud[0] - margin), min(len(self.samples), loud[-1] + 1 + margin)
        return Audio(self.sample_rate, self.samples[start:end])

    def write_wav(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(self.samples.tobytes())
        return path

    @classmethod
    def read_wav(cls, path: str | Path) -> Audio:
        """Read a mono 16-bit WAV (what TTS adapters usually produce)."""
        with wave.open(str(path), "rb") as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2:
                raise ValueError(f"{path} : WAV mono 16 bits attendu")
            samples = array("h")
            samples.frombytes(w.readframes(w.getnframes()))
            return cls(w.getframerate(), samples)
