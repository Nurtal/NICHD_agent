"""Qwen3-TTS worker (Apache-2.0) — run with experiments/voices/.envs/qwen/bin/python.

1. VoiceDesign: two child voices designed from a text description (fully synthetic: no real child),
   saved as references (synth_qwen_girl8, synth_qwen_boy6).
2. Base (voice clone): every item (v1 segments + whole replies) cloned from several references.
3. Emotion through the reference: whole replies cloned from an actress's fearful / sad recording.
"""

from __future__ import annotations

import gc
import sys
import time
import zlib

import numpy as np
import soundfile as sf
import torch
from common import AUDIO, REF, REPLIES, add_reference, items, references, write_rows
from qwen_tts import Qwen3TTSModel

DTYPE = torch.float16  # Turing (TITAN RTX): no native bf16
DESIGNS = {
    "synth_qwen_girl8": (
        "Une petite fille de huit ans, voix d'enfant aiguë et douce, un peu timide, qui parle simplement, "
        "naturellement, sans exagérer.",
        "Le week-end dernier, on est allés à la piscine avec la classe. J'ai fait le grand toboggan, "
        "et après on a mangé des gâteaux dans le car.",
    ),
    "synth_qwen_boy6": (
        "Un petit garçon de six ans, voix d'enfant claire et aiguë, spontané, qui parle naturellement avec "
        "des phrases courtes.",
        "Moi j'aime bien jouer au foot avec mon copain. Hier on a fait un match dans la cour, et j'ai marqué un but.",
    ),
}
CLONE_REFS = ["synth_qwen_girl8", "synth_qwen_boy6", "mls_f1", "mls_f2", "cafe_04_neutre", "synth_kokoro_child"]
EMOTION_REFS = ["cafe_04_peur", "cafe_04_tristesse"]


def load(name: str) -> Qwen3TTSModel:
    return Qwen3TTSModel.from_pretrained(f"Qwen/Qwen3-TTS-12Hz-1.7B-{name}", device_map="cuda:0", dtype=DTYPE,
                                         attn_implementation="sdpa")


BATCH = 8


def design() -> float:
    t = time.perf_counter()
    if all((REF / f"{r}.wav").exists() and r in references() for r in DESIGNS):
        return 0.0
    model = load("VoiceDesign")
    for ref_id, (instruct, text) in DESIGNS.items():
        if (REF / f"{ref_id}.wav").exists() and ref_id in references():
            continue  # already designed: keep the same voice
        torch.manual_seed(zlib.crc32(ref_id.encode()))
        wavs, sr = model.generate_voice_design(text=text, language="French", instruct=instruct)
        sf.write(REF / f"{ref_id}.wav", wavs[0], sr)
        add_reference({"id": ref_id, "kind": "synthétique, voix conçue par description", "source": "Qwen3-TTS VoiceDesign",
                       "licence": "Apache-2.0 (modèle)", "speaker": "aucun (synthèse)", "instruct": instruct,
                       "ref_text": text, "why": "voix d'enfant sans aucun enfant réel (ADR 0002)"})
        print("design", ref_id, round(len(wavs[0]) / sr, 1), "s", file=sys.stderr)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return time.perf_counter() - t


def clone(model, ref_id: str, todo: list[dict], variant: str) -> list[dict]:
    ref = references()[ref_id]
    prompt = model.create_voice_clone_prompt(ref_audio=str(REF / f"{ref_id}.wav"), ref_text=ref["ref_text"],
                                             x_vector_only_mode=False)
    out = AUDIO / variant
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for k in range(0, len(todo), BATCH):
        batch = todo[k : k + BATCH]
        torch.manual_seed(zlib.crc32(batch[0]["id"].encode()))
        torch.cuda.synchronize()
        t = time.perf_counter()
        wavs, sr = model.generate_voice_clone(text=[i["text"] for i in batch], language=["French"] * len(batch),
                                              voice_clone_prompt=prompt)
        torch.cuda.synchronize()
        dt = (time.perf_counter() - t) / len(batch)  # per item, batched
        for item, w in zip(batch, wavs):
            wav = np.asarray(w, dtype=np.float32)
            sf.write(out / f"{item['id']}.wav", wav, sr)
            rows.append({"variant": variant, "rate": 1.0, "id": item["id"], "synth_s": round(dt, 3),
                         "dur_s": round(len(wav) / sr, 3), "ref": ref_id, "batched": len(batch)})
        print(variant, batch[0]["id"], "…", round(dt, 2), "s/élément", file=sys.stderr)
    return rows


def main() -> None:
    design_s = design()
    t = time.perf_counter()
    model = load("Base")
    load_s = time.perf_counter() - t
    torch.cuda.reset_peak_memory_stats()
    rows = []
    for ref_id in CLONE_REFS:
        rows += clone(model, ref_id, items(), f"qwen-{ref_id}")
    for ref_id in EMOTION_REFS:
        rows += clone(model, ref_id, REPLIES, f"qwen-{ref_id}")
    ref = references()["synth_qwen_girl8"]
    p = model.create_voice_clone_prompt(ref_audio=str(REF / "synth_qwen_girl8.wav"), ref_text=ref["ref_text"])
    outs = []
    for _ in range(2):
        torch.manual_seed(1)
        outs.append(model.generate_voice_clone(text=REPLIES[1]["text"], language="French", voice_clone_prompt=p)[0][0])
    meta = {"model": "Qwen/Qwen3-TTS-12Hz-1.7B-Base (+VoiceDesign)", "licence": "Apache-2.0", "dtype": str(DTYPE),
            "load_s": round(load_s, 1), "design_s": round(design_s, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(len(outs[0]) == len(outs[1]) and np.allclose(outs[0], outs[1])), "sample_rate": 24000}
    write_rows("qwen", meta, rows)
    print(meta, len(rows), "items", file=sys.stderr)


if __name__ == "__main__":
    main()
