"""Objective check of the voice-bank candidates (run with the kokoro env: faster-whisper, jiwer, librosa).

Per candidate (4 test replies cloned by Qwen3-TTS Base): Whisper WER, hallucinations, median F0.
A candidate that garbles or invents words is dropped before the listening.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jiwer
import librosa
import numpy as np
from faster_whisper import WhisperModel

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import REPLIES, RES
from evaluate_v2 import norm

BANK = RES / "bank"


def main() -> None:
    cands = json.loads((BANK / "candidates.json").read_text(encoding="utf-8"))
    texts = {r["id"]: r["text"] for r in REPLIES}
    asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    out = []
    for c in cands:
        refs, hyps, f0s, durs = [], [], [], []
        for wav in sorted((BANK / c["id"]).glob("r*.wav")):
            segs, _ = asr.transcribe(str(wav), language="fr", beam_size=5, condition_on_previous_text=False,
                                     without_timestamps=True)
            refs.append(norm(texts[wav.stem]))
            hyps.append(norm(" ".join(s.text for s in segs)) or "∅")
            y, sr = librosa.load(wav, sr=16000)
            f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=600, sr=sr)
            if voiced.any():
                f0s.append(float(np.nanmedian(f0[voiced])))
            durs.append(len(y) / sr / max(1, len(texts[wav.stem])))
        wers = [jiwer.wer(r, h) for r, h in zip(refs, hyps)]
        row = dict(c, wer=float(np.mean(wers)), worst_wer=float(max(wers)), f0=float(np.median(f0s)) if f0s else None,
                   s_per_char=float(np.median(durs)), hyps=hyps)
        row["ok"] = row["worst_wer"] < 0.34 and row["s_per_char"] < 0.12
        out.append(row)
        print(f"{c['id']:18} WER {row['wer']:.0%} (max {row['worst_wer']:.0%})  F0 {row['f0'] or 0:.0f} Hz  "
              f"{'ok' if row['ok'] else 'ÉCARTÉ'}")
    (BANK / "bank_eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
