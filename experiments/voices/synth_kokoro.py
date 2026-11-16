"""Kokoro worker (run with experiments/voices/.envs/kokoro/bin/python).

Variants: native French voice (ff_siwis) and a child version. The child voice raises pitch *and*
formants by resampling (factor F); synthesizing at speed/F first keeps the duration right.
Also writes a ~12 s synthetic child reference clip for the Chatterbox cloning variant."""

from __future__ import annotations

import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline
from scipy.signal import resample_poly

HERE = Path(__file__).parent
RES = HERE / "results"
SR = 24000
CHILD_FACTOR = 1.25  # = 5/4 for exact polyphase resampling; # ≈ +3.9 semitones: adult female F0 ~200 Hz → ~250 Hz (8-year-old range)
SPEED_ITEMS = 15


def synth(pipe: KPipeline, text: str, rate: float, factor: float, seed: int = 0) -> np.ndarray:
    torch.manual_seed(seed)  # the vocoder injects noise: seeded, the output is reproducible
    audio = np.concatenate([a.numpy() for _, _, a in pipe(text, voice="ff_siwis", speed=rate / factor)])
    if factor != 1.0:  # play faster: pitch and formants × factor, duration ÷ factor
        up, down = (4, 5) if factor == 1.25 else (100, round(100 * factor))
        audio = resample_poly(audio, up, down).astype(np.float32)
    return audio


def run(pipe, corpus, variant, factor, rate=1.0, items=None):
    out = RES / "audio" / (variant if rate == 1.0 else f"{variant}@{rate}")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in corpus[:items] if items else corpus:
        torch.cuda.synchronize()
        t = time.perf_counter()
        audio = synth(pipe, item["text"], rate, factor, seed=zlib.crc32(item["id"].encode()))
        torch.cuda.synchronize()
        dt = time.perf_counter() - t
        sf.write(out / f"{item['id']}.wav", audio, SR)
        rows.append({"variant": variant, "rate": rate, "id": item["id"], "synth_s": round(dt, 3),
                     "dur_s": round(len(audio) / SR, 3)})
    return rows


def main() -> None:
    corpus = json.loads((RES / "corpus.json").read_text(encoding="utf-8"))
    t = time.perf_counter()
    pipe = KPipeline(lang_code="f", repo_id="hexgrad/Kokoro-82M", device="cuda")
    load_s = time.perf_counter() - t
    synth(pipe, "Bonjour.", 1.0, 1.0)  # warm-up
    torch.cuda.reset_peak_memory_stats()
    rows = []
    for variant, factor in (("kokoro-siwis", 1.0), ("kokoro-siwis-child", CHILD_FACTOR)):
        rows += run(pipe, corpus, variant, factor)
        rows += run(pipe, corpus, variant, factor, rate=0.75, items=SPEED_ITEMS)
    a = synth(pipe, corpus[2]["text"], 1.0, 1.0)
    b = synth(pipe, corpus[2]["text"], 1.0, 1.0)
    ref_text = ("Le week-end dernier on est allés à la piscine avec la classe. J'ai fait le grand toboggan "
                "avec ma copine Léa, et après on a mangé des gâteaux dans le car.")
    sf.write(RES / "audio" / "ref_kokoro_child.wav", synth(pipe, ref_text, 1.0, CHILD_FACTOR), SR)
    meta = {"engine": "kokoro", "load_s": round(load_s, 1), "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(len(a) == len(b) and np.allclose(a, b)), "sample_rate": SR}
    (RES / "synth_kokoro.jsonl").write_text("\n".join(json.dumps(r) for r in [meta, *rows]) + "\n")
    print(json.dumps(meta), len(rows), "segments", file=sys.stderr)


if __name__ == "__main__":
    main()
