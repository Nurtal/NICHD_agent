"""Fish Audio S2-Pro (Fish Audio Research License, non-commercial) — run with .envs/fish/bin/python.

Starts the fish-speech API server (float16: Turing has no bf16) on one GPU, sends every item with a
cloning reference, stops the server. Drama 3 is left out: it needs ≥ 48 GB in FP8, which Turing lacks.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import ormsgpack
import requests
import soundfile as sf

from common import AUDIO, REF, REPLIES, items, references, write_rows

SRC = Path(__file__).resolve().parent.parent / ".envs" / "fish-src"
URL = "http://127.0.0.1:8090"
CLONE_REFS = ["synth_qwen_girl8", "synth_qwen_boy6", "mls_f1", "mls_f2", "cafe_04_neutre", "synth_kokoro_child"]
EMOTION_REFS = ["cafe_04_peur", "cafe_04_tristesse"]


def start_server() -> subprocess.Popen:
    log = open(Path(__file__).parent / "results_fish_server.log", "w")
    proc = subprocess.Popen([sys.executable, "tools/api_server.py", "--llama-checkpoint-path", "checkpoints/s2-pro",
                             "--half", "--listen", URL.removeprefix("http://")], cwd=SRC, stdout=log, stderr=log,
                            env=dict(os.environ, PYTHONPATH=str(SRC)))
    for _ in range(600):
        time.sleep(2)
        if proc.poll() is not None:
            raise RuntimeError("le serveur Fish s'est arrêté (voir results_fish_server.log)")
        try:
            if requests.get(f"{URL}/v1/health", timeout=2).status_code == 200:
                return proc
        except requests.RequestException:
            pass
    raise RuntimeError("le serveur Fish ne répond pas")


def say(text: str, ref_id: str, seed: int) -> tuple[np.ndarray, int]:
    ref = references()[ref_id]
    payload = {"text": text, "references": [{"audio": (REF / f"{ref_id}.wav").read_bytes(), "text": ref["ref_text"]}],
               "format": "wav", "seed": seed}
    r = requests.post(f"{URL}/v1/tts", data=ormsgpack.packb(payload),
                      headers={"Content-Type": "application/msgpack"}, timeout=600)
    r.raise_for_status()
    import io
    wav, sr = sf.read(io.BytesIO(r.content), dtype="float32")
    return wav, sr


def main() -> None:
    t = time.perf_counter()
    server = start_server()
    load_s = time.perf_counter() - t
    rows, sr = [], 44100
    try:
        def run(variant, ref_id, todo):
            nonlocal sr
            out = AUDIO / variant
            out.mkdir(parents=True, exist_ok=True)
            for item in todo:
                t0 = time.perf_counter()
                wav, sr = say(item["text"], ref_id, zlib.crc32(item["id"].encode()) % (2 ** 31))
                dt = time.perf_counter() - t0
                sf.write(out / f"{item['id']}.wav", wav, sr)
                rows.append({"variant": variant, "rate": 1.0, "id": item["id"], "synth_s": round(dt, 3),
                             "dur_s": round(len(wav) / sr, 3), "ref": ref_id})
                print(variant, item["id"], round(dt, 2), file=sys.stderr)

        for ref_id in CLONE_REFS:
            run(f"fish-{ref_id}", ref_id, items())
        for ref_id in EMOTION_REFS:
            run(f"fish-{ref_id}", ref_id, REPLIES)
        a, _ = say("C'était dimanche soir.", "synth_qwen_girl8", 1)
        b, _ = say("C'était dimanche soir.", "synth_qwen_girl8", 1)
        meta = {"model": "fishaudio/s2-pro", "licence": "Fish Audio Research License (non commerciale)",
                "dtype": "float16", "load_s": round(load_s, 1), "peak_gpu_gb": None,
                "deterministic": bool(len(a) == len(b) and np.allclose(a, b)), "sample_rate": sr}
        write_rows("fish", meta, rows)
        print(meta, file=sys.stderr)
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
