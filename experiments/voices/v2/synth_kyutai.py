"""Kyutai TTS 1.6B en/fr (CC BY 4.0) — run with experiments/voices/.envs/kyutai/bin/python.

Kyutai does not release free voice cloning: only pre-computed voice embeddings (kyutai/tts-voices).
Its French voices come from CML-TTS, i.e. the same MLS readers as our references: 10179 (= mls_f1,
children's tales) and 12080, in their "enhanced" (denoised) versions.
"""

from __future__ import annotations

import sys
import time
import zlib

import numpy as np
import soundfile as sf
import torch
from common import AUDIO, items, write_rows
from moshi.models.loaders import CheckpointInfo
from moshi.models.tts import DEFAULT_DSM_TTS_REPO, TTSModel

VOICES = {
    "kyutai-mls10179": "cml-tts/fr/10179_11051_000005-0001_enhanced.wav",
    "kyutai-mls12080": "cml-tts/fr/12080_11650_000047-0001_enhanced.wav",
}


def synth(model, text: str, voice_path: str, seed: int) -> np.ndarray:
    torch.manual_seed(seed)
    entries = model.prepare_script([text], padding_between=1)
    cond = model.make_condition_attributes([voice_path], cfg_coef=2.0)
    result = model.generate([entries], [cond])
    with model.mimi.streaming(1), torch.no_grad():
        pcm = [model.mimi.decode(f[:, 1:, :]).cpu().numpy()[0, 0] for f in result.frames[model.delay_steps:]]
    return np.clip(np.concatenate(pcm), -1, 1).astype(np.float32)


def main() -> None:
    t = time.perf_counter()
    model = TTSModel.from_checkpoint_info(CheckpointInfo.from_hf_repo(DEFAULT_DSM_TTS_REPO), n_q=32, temp=0.6,
                                          device="cuda", dtype=torch.float16)
    load_s = time.perf_counter() - t
    sr = model.mimi.sample_rate
    torch.cuda.reset_peak_memory_stats()
    rows = []
    for variant, voice in VOICES.items():
        path = model.get_voice_path(voice)
        out = AUDIO / variant
        out.mkdir(parents=True, exist_ok=True)
        for item in items():
            torch.cuda.synchronize()
            t = time.perf_counter()
            wav = synth(model, item["text"], path, zlib.crc32(item["id"].encode()))
            torch.cuda.synchronize()
            dt = time.perf_counter() - t
            sf.write(out / f"{item['id']}.wav", wav, sr)
            rows.append({"variant": variant, "rate": 1.0, "id": item["id"], "synth_s": round(dt, 3),
                         "dur_s": round(len(wav) / sr, 3), "ref": voice})
            print(variant, item["id"], round(dt, 2), file=sys.stderr)
    path = model.get_voice_path(VOICES["kyutai-mls10179"])
    a, b = synth(model, "C'était dimanche soir.", path, 1), synth(model, "C'était dimanche soir.", path, 1)
    meta = {"model": "kyutai/tts-1.6b-en_fr", "licence": "CC-BY-4.0 (voix : licences CML-TTS)", "load_s": round(load_s, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(len(a) == len(b) and np.allclose(a, b)), "sample_rate": sr}
    write_rows("kyutai", meta, rows)
    print(meta, file=sys.stderr)


if __name__ == "__main__":
    main()
