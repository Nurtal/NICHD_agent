"""Speaker port (TTS) and the dependency-free tone speaker."""

from __future__ import annotations

import math
from array import array
from typing import Protocol

from nichd_sim.voice.audio import Audio


class Speaker(Protocol):
    """Text-to-speech for one speech chunk. Silences are never asked of the TTS: the
    assembler inserts them, so that timing is exact and replayable (ADR 0002)."""

    sample_rate: int

    def synthesize(self, text: str, *, rate: float = 1.0) -> Audio:
        """Speak `text` at the relative `rate` (1.0 = normal, lower = slower)."""
        ...


class ToneSpeaker:
    """Stand-in voice: a hum whose length follows the text. No dependency, deterministic.
    For tests and for checking the timing of a session without a TTS model."""

    def __init__(self, sample_rate: int = 22050, ms_per_char: float = 55.0, pitch_hz: float = 260.0):
        self.sample_rate = sample_rate
        self.ms_per_char = ms_per_char
        self.pitch_hz = pitch_hz

    def synthesize(self, text: str, *, rate: float = 1.0) -> Audio:
        n = round(self.sample_rate * len(text.strip()) * self.ms_per_char / 1000 / max(rate, 0.1))
        fade = max(1, min(n // 2, self.sample_rate // 100))  # 10 ms fade in/out, no clicks
        samples = array("h")
        for i in range(n):
            env = min(1.0, i / fade, (n - 1 - i) / fade)
            samples.append(int(8000 * env * math.sin(2 * math.pi * self.pitch_hz * i / self.sample_rate)))
        return Audio(self.sample_rate, samples)
