"""Kokoro TTS worker — runs in Kokoro's own venv, NOT in the project's (see experiments/voices/README.md).

Standalone script (no nichd_sim import). Protocol: one JSON request per stdin line, one JSON
response per stdout line.

    {"pieces": ["euh…", "Je suis allée dans ma chambre,", "et après j'ai pleuré."],
     "rate": 0.9, "seed": 123, "voice": "ff_siwis", "factor": 1.25}
    → {"sample_rate": 24000, "pieces": ["<base64 int16 PCM>", ...]}

The pieces are synthesized as ONE utterance (continuous intonation, « euh » in context), then cut
at the piece boundaries using Kokoro's own predicted phoneme durations. `factor` > 1 raises pitch
and formants (child voice) by resampling, after synthesizing at speed/factor so the duration holds.
"""

from __future__ import annotations

import base64
import json
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import torch
from kokoro import KPipeline
from scipy.signal import resample_poly

SR = 24000
SAMPLES_PER_FRAME = 600  # Kokoro duration unit
MAX_PHONEMES = 500  # Kokoro's context is 510 phonemes: longer replies are synthesized in batches


def _ratio(factor: float) -> tuple[int, int]:
    """Resampling ratio (up, down) for a pitch factor, exact for 1.25 = 5/4."""
    return (4, 5) if abs(factor - 1.25) < 1e-9 else (100, round(100 * factor))


def _batches(phonemes: list[str]) -> list[list[int]]:
    """Group piece indices so that each batch stays under Kokoro's phoneme limit."""
    batches, current, size = [], [], 0
    for i, ps in enumerate(phonemes):
        if current and size + len(ps) + 1 > MAX_PHONEMES:
            batches.append(current)
            current, size = [], 0
        current.append(i)
        size += len(ps) + 1
    if current:
        batches.append(current)
    return batches


def synthesize(pipe: KPipeline, pieces: list[str], rate: float, voice: str, factor: float) -> list[np.ndarray]:
    phonemes = [pipe.g2p(p)[0] or "" for p in pieces]
    out: list[np.ndarray] = [np.zeros(0, dtype=np.float32)] * len(pieces)
    for batch in _batches(phonemes):
        joined = " ".join(phonemes[i] for i in batch)
        results = list(pipe.generate_from_tokens(joined, voice=voice, speed=rate / factor))
        audio = np.concatenate([r.audio.numpy() for r in results])
        durations = torch.cat([r.pred_dur for r in results]).tolist() if len(results) == 1 else None
        if durations is None:  # split internally despite the limit: fall back to proportional cuts
            cuts = np.cumsum([len(phonemes[i]) + 1 for i in batch])[:-1] / (len(joined) + 1) * len(audio)
        else:
            # durations[0] is the start token; phoneme k of `joined` is durations[1 + k].
            frames = np.cumsum([0] + durations)
            cuts, offset = [], 0
            for i in batch[:-1]:
                offset += len(phonemes[i])  # index of the separating space in `joined`
                start, end = frames[1 + offset], frames[2 + offset]
                cuts.append((start + end) / 2 * SAMPLES_PER_FRAME)  # middle of the word gap
                offset += 1
        bounds = [0, *[int(c) for c in cuts], len(audio)]
        for k, i in enumerate(batch):
            out[i] = audio[bounds[k] : bounds[k + 1]]
    if factor != 1.0:
        up, down = _ratio(factor)
        out = [resample_poly(a, up, down).astype(np.float32) if len(a) else a for a in out]
    return out


def _pcm(audio: np.ndarray) -> str:
    return base64.b64encode((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()).decode()


def main() -> None:
    pipe = None
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            if pipe is None:
                pipe = KPipeline(lang_code="f", repo_id="hexgrad/Kokoro-82M",
                                 device="cuda" if torch.cuda.is_available() else "cpu")
            torch.manual_seed(int(req.get("seed", 0)))  # the vocoder injects noise
            audios = synthesize(pipe, req["pieces"], float(req.get("rate", 1.0)),
                                req.get("voice", "ff_siwis"), float(req.get("factor", 1.0)))
            resp = {"sample_rate": SR, "pieces": [_pcm(a) for a in audios]}
        except Exception as e:  # report and keep serving
            resp = {"error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
