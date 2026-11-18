"""Higgs TTS 3 4B (Boson AI, research / non-commercial licence) — run with .envs/higgs/bin/python.

transformers port (multimodalart/higgs-audio-v3-tts-4b-transformers, original weights). Same cloning
references as the other engines, plus emotion through inline tags on the whole replies
(<|emotion:fear|>, sadness, shame): a possible bridge from the engine's arousal to the voice.
"""

from __future__ import annotations

import sys
import time
import zlib

import numpy as np
import soundfile as sf
import torch
from common import AUDIO, REF, REPLIES, items, references, write_rows
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO = "multimodalart/higgs-audio-v3-tts-4b-transformers"
DTYPE = torch.float16 if "--fp16" in sys.argv else torch.float32  # Turing: no bf16
CLONE_REFS = ["synth_qwen_girl8", "synth_qwen_boy6", "mls_f1", "mls_f2", "cafe_04_neutre", "synth_kokoro_child"]
EMOTIONS = ["fear", "sadness", "shame"]


def main() -> None:
    t = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(REPO)
    model = AutoModelForCausalLM.from_pretrained(REPO, trust_remote_code=True, dtype=DTYPE).to("cuda").eval()
    load_s = time.perf_counter() - t
    sr = model.config.sample_rate
    refs = references()
    torch.cuda.reset_peak_memory_stats()
    rows = []

    def say(text, ref_id, seed):
        data, rsr = sf.read(str(REF / f"{ref_id}.wav"), dtype="float32", always_2d=True)
        ref = torch.from_numpy(data.T.copy())  # [channels, samples]; torchaudio.load needs torchcodec
        torch.manual_seed(seed)
        wav = model.generate_speech(text, tok, reference_audio=ref, reference_sample_rate=rsr,
                                    reference_text=refs[ref_id]["ref_text"], temperature=0.7, top_p=0.95)
        return wav.float().numpy()

    def run(variant, ref_id, todo, prefix=""):
        out = AUDIO / variant
        out.mkdir(parents=True, exist_ok=True)
        for item in todo:
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            wav = say(prefix + item["text"], ref_id, zlib.crc32(item["id"].encode()))
            torch.cuda.synchronize()
            dt = time.perf_counter() - t0
            sf.write(out / f"{item['id']}.wav", wav, sr)
            rows.append({"variant": variant, "rate": 1.0, "id": item["id"], "synth_s": round(dt, 3),
                         "dur_s": round(len(wav) / sr, 3), "ref": ref_id, "tags": prefix})
            print(variant, item["id"], round(dt, 2), file=sys.stderr)

    for ref_id in CLONE_REFS:
        run(f"higgs-{ref_id}", ref_id, items())
    for emo in EMOTIONS:
        run(f"higgs-synth_qwen_girl8+{emo}", "synth_qwen_girl8", REPLIES, prefix=f"<|emotion:{emo}|>")
    a, b = say("C'était dimanche soir.", "synth_qwen_girl8", 1), say("C'était dimanche soir.", "synth_qwen_girl8", 1)
    meta = {"model": REPO, "licence": "Boson Higgs TTS 3 research / non-commercial", "dtype": str(DTYPE),
            "load_s": round(load_s, 1), "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(len(a) == len(b) and np.allclose(a, b)), "sample_rate": sr}
    write_rows("higgs", meta, rows)
    print(meta, file=sys.stderr)


if __name__ == "__main__":
    main()
