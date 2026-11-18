"""XTTS v2 (Coqui CPML, non-commercial) and Chatterbox Multilingual v3 (MIT) — voice cloning workers.

    COQUI_TOS_AGREED=1 ../.envs/xtts/bin/python synth_clone_engines.py xtts
    ../.envs/chatterbox/bin/python synth_clone_engines.py chatterbox

Same references as Qwen: designed child voices (synthetic), MLS readers, a CaFE actress, Kokoro child.
"""

from __future__ import annotations

import sys
import time
import zlib

import numpy as np
import soundfile as sf
import torch

from common import AUDIO, REF, REPLIES, items, write_rows

CLONE_REFS = ["synth_qwen_girl8", "synth_qwen_boy6", "mls_f1", "mls_f2", "cafe_04_neutre", "synth_kokoro_child"]
EMOTION_REFS = ["cafe_04_peur", "cafe_04_tristesse"]


class Xtts:
    name, licence = "xtts", "Coqui Public Model License (non commerciale)"

    def __init__(self):
        from TTS.api import TTS
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
        self.sr = self.tts.synthesizer.output_sample_rate

    def say(self, text, ref):
        return np.asarray(self.tts.tts(text=text, speaker_wav=str(ref), language="fr"), dtype=np.float32)


class Chatterbox:
    name, licence = "chatterbox3", "MIT (filigrane Perth dans l'audio)"

    def __init__(self):
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        self.model = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
        self.sr = self.model.sr

    def say(self, text, ref):
        return self.model.generate(text, language_id="fr", audio_prompt_path=str(ref)).squeeze(0).cpu().numpy()


def run(engine, ref_id, todo, rows):
    variant = f"{engine.name}-{ref_id}"
    out = AUDIO / variant
    out.mkdir(parents=True, exist_ok=True)
    for item in todo:
        torch.manual_seed(zlib.crc32(item["id"].encode()))
        torch.cuda.synchronize()
        t = time.perf_counter()
        wav = engine.say(item["text"], REF / f"{ref_id}.wav")
        torch.cuda.synchronize()
        dt = time.perf_counter() - t
        sf.write(out / f"{item['id']}.wav", wav, engine.sr)
        rows.append({"variant": variant, "rate": 1.0, "id": item["id"], "synth_s": round(dt, 3),
                     "dur_s": round(len(wav) / engine.sr, 3), "ref": ref_id})
        print(variant, item["id"], round(dt, 2), file=sys.stderr)


def main() -> None:
    engine_cls = {"xtts": Xtts, "chatterbox": Chatterbox}[sys.argv[1]]
    t = time.perf_counter()
    engine = engine_cls()
    load_s = time.perf_counter() - t
    torch.cuda.reset_peak_memory_stats()
    rows = []
    for ref_id in CLONE_REFS:
        run(engine, ref_id, items(), rows)
    for ref_id in EMOTION_REFS:
        run(engine, ref_id, REPLIES, rows)
    outs = []
    for _ in range(2):
        torch.manual_seed(1)
        outs.append(engine.say("C'était dimanche soir.", REF / "synth_qwen_girl8.wav"))
    meta = {"model": engine.name, "licence": engine.licence, "load_s": round(load_s, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(len(outs[0]) == len(outs[1]) and np.allclose(outs[0], outs[1])), "sample_rate": engine.sr}
    write_rows(engine.name, meta, rows)
    print(meta, file=sys.stderr)


if __name__ == "__main__":
    main()
