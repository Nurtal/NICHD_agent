"""Qwen3-TTS worker — runs in Qwen's own venv, NOT in the project's (see experiments/voices/README.md).

Standalone script (no nichd_sim import). Protocol: one JSON request per stdin line, one JSON
response per stdout line.

    {"text": "Euh… il m'a attrapé le bras.", "ref_audio": "/…/fille_7_9.flac", "ref_text": "…",
     "seed": 123, "rate": 0.9}
    → {"sample_rate": 24000, "audio": "<base64 int16 PCM>"}

The whole reply is said in one go by Qwen3-TTS Base, cloning a child voice designed from a text
description (synthetic: no real child, ADR 0002). Pauses and fillers are written in the text (« … »,
« euh… »); the caller re-times the pauses to the engine's plan. `rate` ≠ 1 stretches the audio, pitch
kept. Turing GPUs have no bf16: float16.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np
import torch

MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def _load():
    from qwen_tts import Qwen3TTSModel

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device != "cpu" else torch.float32
    return Qwen3TTSModel.from_pretrained(MODEL, device_map=device, dtype=dtype, attn_implementation="sdpa")


def _stretch(audio: np.ndarray, rate: float) -> np.ndarray:
    if abs(rate - 1.0) < 1e-3 or not len(audio):
        return audio
    import librosa

    return librosa.effects.time_stretch(audio, rate=rate).astype(np.float32)


def _pcm(audio: np.ndarray) -> str:
    return base64.b64encode((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()).decode()


def main() -> None:
    model, prompts = None, {}
    real_stdout = sys.stdout
    sys.stdout = sys.stderr  # the model's own prints must not corrupt the protocol
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            if model is None:
                model = _load()
            key = (req["ref_audio"], req["ref_text"])
            if key not in prompts:  # one clone prompt per voice, reused for every reply
                prompts[key] = model.create_voice_clone_prompt(ref_audio=req["ref_audio"], ref_text=req["ref_text"])
            torch.manual_seed(int(req.get("seed", 0)))
            wavs, sr = model.generate_voice_clone(text=req["text"], language="French", voice_clone_prompt=prompts[key])
            audio = _stretch(np.asarray(wavs[0], dtype=np.float32), float(req.get("rate", 1.0)))
            resp = {"sample_rate": int(sr), "audio": _pcm(audio)}
        except Exception as e:  # noqa: BLE001 — report and keep serving
            resp = {"error": f"{type(e).__name__}: {e}"}
        real_stdout.write(json.dumps(resp) + "\n")
        real_stdout.flush()


if __name__ == "__main__":
    main()
