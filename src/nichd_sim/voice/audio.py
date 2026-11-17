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

    def faded(self, ms: int = 8) -> Audio:
        """Short linear fade in/out: no click where a piece was cut out of an utterance."""
        n = min(len(self.samples) // 2, round(self.sample_rate * ms / 1000))
        if n == 0:
            return self
        s = array("h", self.samples)
        for i in range(n):
            g = i / n
            s[i] = int(s[i] * g)
            s[-1 - i] = int(s[-1 - i] * g)
        return Audio(self.sample_rate, s)

    def voiced_bounds(self, frame_ms: int = 20, rel: float = 0.1, floor: int = 200, noise_ratio: float = 2.5,
                      min_frames: int = 3) -> tuple[int, int] | None:
        """(start_ms, end_ms) of the sound, by frame energy. More precise than STT word timings
        for measuring turn-taking.

        A frame is loud above max(`floor`, `rel` × the loudest frame, `noise_ratio` × the noise
        floor), where the noise floor is the 10th percentile of frame energy (voice evaluation N4:
        without it, noise at 10 dB SNR counted as speech from the first frame). Speech starts (ends)
        at the first (last) run of `min_frames` loud frames, so an isolated click is ignored, then
        extends over the soft edges of speech while the energy stays above 1.5 × the noise floor."""
        n = max(1, round(self.sample_rate * frame_ms / 1000))
        rms = []
        for i in range(0, len(self.samples), n):
            frame = self.samples[i : i + n]
            rms.append((sum(s * s for s in frame) / len(frame)) ** 0.5 if frame else 0.0)
        if not rms or max(rms) < floor:
            return None
        noise = sorted(rms)[len(rms) // 10]
        threshold = max(floor, rel * max(rms), min(noise_ratio * noise, 0.5 * max(rms)))
        loud = [v >= threshold for v in rms]
        runs = [i for i in range(len(loud) - min_frames + 1) if all(loud[i : i + min_frames])]
        if not runs:
            return None
        # Hysteresis: extend over the soft edges of speech (onset consonants, final decay) while the
        # energy stays clearly above the noise floor.
        low = max(floor, 1.5 * noise) if noise > 0 else threshold
        start, end = runs[0], runs[-1] + min_frames - 1
        while start > 0 and rms[start - 1] >= low:
            start -= 1
        while end < len(rms) - 1 and rms[end + 1] >= low:
            end += 1
        return start * frame_ms, (end + 1) * frame_ms

    def mix_at(self, other: Audio, at_ms: int) -> None:
        """Add `other` starting at `at_ms`, extending with silence as needed (overlaps are summed)."""
        if other.sample_rate != self.sample_rate:
            raise ValueError(f"fréquences d'échantillonnage différentes : {other.sample_rate} ≠ {self.sample_rate}")
        start = round(self.sample_rate * at_ms / 1000)
        end = start + len(other.samples)
        if end > len(self.samples):
            self.samples.extend(array("h", bytes(2 * (end - len(self.samples)))))
        for i, s in enumerate(other.samples):
            self.samples[start + i] = max(-32768, min(32767, self.samples[start + i] + s))

    def resampled(self, sample_rate: int) -> Audio:
        """Linear-interpolation resampling: good enough for a listening track, not for analysis."""
        if sample_rate == self.sample_rate or not self.samples:
            return Audio(sample_rate, array("h", self.samples))
        n = round(len(self.samples) * sample_rate / self.sample_rate)
        src, out = self.samples, array("h")
        step = (len(src) - 1) / max(1, n - 1)
        for i in range(n):
            x = i * step
            k = int(x)
            frac = x - k
            nxt = src[min(k + 1, len(src) - 1)]
            out.append(int(src[k] + (nxt - src[k]) * frac))
        return Audio(sample_rate, out)

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
