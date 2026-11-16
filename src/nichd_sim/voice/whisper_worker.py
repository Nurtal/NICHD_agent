"""faster-whisper STT worker — runs in the voice venv, NOT in the project's (experiments/voices/README.md).

Standalone script (no nichd_sim import). One JSON request per stdin line, one response per line:

    {"pcm": "<base64 int16 mono>", "sample_rate": 24000, "prompt": null, "model": "large-v3"}
    → {"text": "Dis-moi tout.", "words": [["Dis-moi", 120, 480], ["tout.", 480, 800]]}

Voice-activity filtering is on: Whisper otherwise hallucinates text on silence.
"""

from __future__ import annotations

import base64
import json
import sys
import warnings
from math import gcd

warnings.filterwarnings("ignore")

import numpy as np
from faster_whisper import WhisperModel
from scipy.signal import resample_poly

ASR_RATE = 16000


def load(name: str) -> WhisperModel:
    try:
        return WhisperModel(name, device="cuda", compute_type="float16")
    except Exception:  # noqa: BLE001 — no GPU / cuDNN: CPU works, slower
        return WhisperModel(name, device="cpu", compute_type="int8")


def main() -> None:
    models: dict[str, WhisperModel] = {}
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            name = req.get("model", "large-v3")
            if name not in models:
                models[name] = load(name)
            pcm = np.frombuffer(base64.b64decode(req["pcm"]), dtype="<i2").astype(np.float32) / 32768
            sr = int(req["sample_rate"])
            if sr != ASR_RATE:
                g = gcd(ASR_RATE, sr)
                pcm = resample_poly(pcm, ASR_RATE // g, sr // g).astype(np.float32)
            segments, _ = models[name].transcribe(
                pcm, language="fr", beam_size=5, word_timestamps=True, vad_filter=True,
                condition_on_previous_text=False, initial_prompt=req.get("prompt"),
            )
            words, texts = [], []
            for seg in segments:
                texts.append(seg.text.strip())
                words += [[w.word.strip(), round(w.start * 1000), round(w.end * 1000)] for w in seg.words or []]
            resp = {"text": " ".join(t for t in texts if t), "words": words}
        except Exception as e:  # noqa: BLE001 — report and keep serving
            resp = {"error": f"{type(e).__name__}: {e}"}
        sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
