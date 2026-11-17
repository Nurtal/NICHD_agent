"""F5-TTS French (RASPIAUDIO/F5-French-MixedSpeakers-reduced, CC BY-NC 4.0, LibriVox) — run with .envs/f5/bin/python.

The only Quebec fine-tune found was set aside (accent mismatch); this is its France-French base.
"""

from __future__ import annotations

import sys
import time
import zlib

import numpy as np
import soundfile as sf
import torch
from common import AUDIO, REF, REPLIES, items, references, write_rows
from f5_tts.api import F5TTS
from huggingface_hub import hf_hub_download

REPO = "RASPIAUDIO/F5-French-MixedSpeakers-reduced"
CLONE_REFS = ["synth_qwen_girl8", "synth_qwen_boy6", "mls_f1", "mls_f2", "cafe_04_neutre", "synth_kokoro_child"]
EMOTION_REFS = ["cafe_04_peur", "cafe_04_tristesse"]


def main() -> None:
    t = time.perf_counter()
    tts = F5TTS(model="F5TTS_Base", ckpt_file=hf_hub_download(REPO, "model_last_reduced.pt"),
                vocab_file=hf_hub_download(REPO, "vocab.txt"), device="cuda")
    load_s = time.perf_counter() - t
    refs = references()
    torch.cuda.reset_peak_memory_stats()
    rows, sr = [], 24000

    def say(text, ref_id, seed):
        wav, rate, _ = tts.infer(str(REF / f"{ref_id}.wav"), refs[ref_id]["ref_text"], text, seed=seed,
                                 show_info=lambda *a: None, progress=None)
        return np.asarray(wav, dtype=np.float32), rate

    def run(ref_id, todo):
        nonlocal sr
        variant = f"f5-{ref_id}"
        out = AUDIO / variant
        out.mkdir(parents=True, exist_ok=True)
        for item in todo:
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            wav, sr = say(item["text"], ref_id, zlib.crc32(item["id"].encode()) % (2 ** 31))
            torch.cuda.synchronize()
            dt = time.perf_counter() - t0
            sf.write(out / f"{item['id']}.wav", wav, sr)
            rows.append({"variant": variant, "rate": 1.0, "id": item["id"], "synth_s": round(dt, 3),
                         "dur_s": round(len(wav) / sr, 3), "ref": ref_id})
            print(variant, item["id"], round(dt, 2), file=sys.stderr)

    for ref_id in CLONE_REFS:
        run(ref_id, items())
    for ref_id in EMOTION_REFS:
        run(ref_id, REPLIES)
    a, _ = say("C'était dimanche soir.", "synth_qwen_girl8", 1)
    b, _ = say("C'était dimanche soir.", "synth_qwen_girl8", 1)
    meta = {"model": REPO, "licence": "CC-BY-NC-4.0", "load_s": round(load_s, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(len(a) == len(b) and np.allclose(a, b)), "sample_rate": sr}
    write_rows("f5", meta, rows)
    print(meta, file=sys.stderr)


if __name__ == "__main__":
    main()
