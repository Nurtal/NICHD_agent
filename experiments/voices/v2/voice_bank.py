"""Child voice bank: Qwen3-TTS VoiceDesign candidates per (gender, age band) — run with .envs/qwen/bin/python.

The blind listening put the designed 8-year-old girl far ahead (naturalness 4.8/5) and showed that the
reference matters more than the engine. Scenarios have girls and boys aged 5 to 12, so: 4 designed
candidates per slot (2 descriptions × 2 seeds), each then cloned by Qwen3-TTS Base on test replies,
exactly as the speaker will run. Fully synthetic voices only (ADR 0002). The validated girl8 voice fills
the girl 8–10 slot as is.

    CUDA_VISIBLE_DEVICES=0 ../.envs/qwen/bin/python voice_bank.py
"""

from __future__ import annotations

import gc
import json
import sys
import zlib

import numpy as np
import soundfile as sf
import torch
from common import REF, REPLIES, RES, references
from qwen_tts import Qwen3TTSModel

DTYPE = torch.float16
BANK = RES / "bank"
TEST_REPLIES = ["r03", "r05", "r09", "r11"]
STYLE = ("parle naturellement, simplement, avec des phrases courtes, sans exagérer ni jouer la comédie, "
         "comme un enfant qui répond à un adulte qu'il ne connaît pas bien.")
TEXTS = {
    "5_7": "Moi j'ai un chat, il s'appelle Pompon. Il dort sur mon lit et des fois il me griffe un petit peu.",
    "8_10": "Le week-end dernier, on est allés à la piscine avec la classe. J'ai fait le grand toboggan, "
            "et après on a mangé des gâteaux dans le car.",
    "11_12": "Cette année je suis en sixième. Il y a beaucoup plus de devoirs qu'avant, mais j'aime bien "
             "les cours de sport et de musique.",
}
SLOTS = {
    ("fille", "5_7"): ["Une petite fille de six ans, voix d'enfant très aiguë, claire et douce",
                       "Une fillette de cinq ans et demi, petite voix fluette et un peu hésitante"],
    ("fille", "11_12"): ["Une fille de onze ans, voix d'enfant encore aiguë mais plus posée, un peu réservée",
                         "Une préadolescente de douze ans, voix claire et jeune, légèrement timide"],
    ("garcon", "5_7"): ["Un petit garçon de six ans, voix d'enfant aiguë et claire, un peu timide",
                        "Un garçon de cinq ans, petite voix d'enfant très jeune, douce et spontanée"],
    ("garcon", "8_10"): ["Un garçon de neuf ans, voix d'enfant aiguë qui n'a pas mué, un peu réservée",
                         "Un écolier de huit ans, voix d'enfant claire et vive, encore très jeune"],
    ("garcon", "11_12"): ["Un garçon de onze ans dont la voix n'a pas encore mué, voix d'enfant claire, un peu "
                          "timide",
                          "Un garçon de douze ans, voix d'enfant encore aiguë, sans mue, posée et réservée"],
}
VALIDATED = {("fille", "8_10"): "synth_qwen_girl8"}


def load(name: str) -> Qwen3TTSModel:
    return Qwen3TTSModel.from_pretrained(f"Qwen/Qwen3-TTS-12Hz-1.7B-{name}", device_map="cuda:0", dtype=DTYPE,
                                         attn_implementation="sdpa")


def design(cands: list[dict]) -> None:
    todo = [c for c in cands if not (BANK / "refs" / f"{c['id']}.wav").exists()]
    if not todo:
        return
    model = load("VoiceDesign")
    for c in todo:
        torch.manual_seed(c["seed"])
        wavs, sr = model.generate_voice_design(text=c["ref_text"], language="French", instruct=c["instruct"])
        sf.write(BANK / "refs" / f"{c['id']}.wav", np.asarray(wavs[0], dtype=np.float32), sr)
        print("design", c["id"], round(len(wavs[0]) / sr, 1), "s", file=sys.stderr)
    del model
    gc.collect()
    torch.cuda.empty_cache()


def main() -> None:
    (BANK / "refs").mkdir(parents=True, exist_ok=True)
    cands = []
    for (gender, band), descriptions in SLOTS.items():
        for d, desc in enumerate(descriptions):
            for s in range(2):
                cid = f"{gender}_{band}_{'ab'[d]}{s + 1}"
                cands.append({"id": cid, "gender": gender, "band": band, "instruct": f"{desc}. Elle {STYLE}"
                              if gender == "fille" else f"{desc}. Il {STYLE}", "ref_text": TEXTS[band],
                              "seed": zlib.crc32(cid.encode())})
    design(cands)
    for (gender, band), ref_id in VALIDATED.items():
        r = references()[ref_id]
        data, sr = sf.read(REF / f"{ref_id}.wav", dtype="float32")
        sf.write(BANK / "refs" / f"{gender}_{band}_v.wav", data, sr)
        cands.append({"id": f"{gender}_{band}_v", "gender": gender, "band": band, "instruct": r["instruct"],
                      "ref_text": r["ref_text"], "seed": None, "validated": ref_id})
    model = load("Base")
    texts = {r["id"]: r["text"] for r in REPLIES}
    for c in cands:
        out = BANK / c["id"]
        out.mkdir(exist_ok=True)
        prompt = model.create_voice_clone_prompt(ref_audio=str(BANK / "refs" / f"{c['id']}.wav"), ref_text=c["ref_text"])
        torch.manual_seed(1)
        wavs, sr = model.generate_voice_clone(text=[texts[i] for i in TEST_REPLIES], language=["French"] * len(TEST_REPLIES),
                                              voice_clone_prompt=prompt)
        for rid, w in zip(TEST_REPLIES, wavs):
            sf.write(out / f"{rid}.wav", np.asarray(w, dtype=np.float32), sr)
        print("clone", c["id"], file=sys.stderr)
    (BANK / "candidates.json").write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
