"""Objective screening of the v2 variants (run with the kokoro env: faster-whisper, jiwer, librosa).

Per variant: intelligibility (Whisper large-v3 WER/CER) on sentences, fragments and whole replies,
hallucinations, median F0 (an 8-year-old ≈ 250–300 Hz), pace, synthesis speed (RTF), and, for the whole
replies, whether the written pauses (« … ») are really rendered as pauses. Baselines from v1: the current
voice (kokoro-siwis-child) and the Chatterbox clone of it.
"""

from __future__ import annotations

import json
import re
import statistics as st
import sys
import unicodedata
from pathlib import Path

import jiwer
import librosa
import numpy as np
from faster_whisper import WhisperModel

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import AUDIO, RES, items  # noqa: E402

V1 = HERE.parent / "results"
BASELINES = ["kokoro-siwis-child", "chatterbox-clone-kchild"]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text.replace("’", "'").lower())
    text = re.sub(r"\b(euh+|hein)\b", " ", text)
    text = re.sub(r"[^\w' -]", " ", text).replace("-", " ")
    return " ".join(text.split())


def load_rows() -> tuple[dict, list[dict]]:
    meta, rows = {}, []
    for path in sorted(RES.glob("synth_*.jsonl")):
        lines = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
        meta[lines[0]["engine"]] = lines[0]
        rows += [dict(r, engine=lines[0]["engine"], wav=str(AUDIO / r["variant"] / f"{r['id']}.wav")) for r in lines[1:]]
    v1 = [json.loads(ln) for p in V1.glob("synth_*.jsonl") for ln in p.read_text().splitlines()[1:] if ln.strip()]
    for r in v1:
        if r["variant"] in BASELINES and r["rate"] == 1.0:
            rows.append(dict(r, engine="v1", wav=str(V1 / "audio" / r["variant"] / f"{r['id']}.wav")))
    return meta, rows


def pauses(y: np.ndarray, sr: int, min_ms: int = 180) -> int:
    """Inner quiet stretches ≥ min_ms between the first and last sound."""
    rms = librosa.feature.rms(y=y, frame_length=480, hop_length=320)[0]
    loud = rms > 0.08 * rms.max()
    idx = np.flatnonzero(loud)
    if len(idx) < 2:
        return 0
    inner = ~loud[idx[0] : idx[-1]]
    count, run = 0, 0
    for q in inner:
        run = run + 1 if q else 0
        if run * 20 == min_ms:
            count += 1
    return count


def main() -> None:
    texts = {i["id"]: i["text"] for i in items()}
    meta, rows = load_rows()
    try:
        asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:
        asr = WhisperModel("large-v3", device="cpu", compute_type="int8")
    cache_path = RES / "eval.jsonl"
    cache = {}
    if cache_path.exists():  # reuse earlier measurements of unchanged files
        for ln in cache_path.read_text().splitlines():
            if ln.strip():
                c = json.loads(ln)
                cache[(c["wav"], c.get("mtime"))] = c
    out = []
    for k, r in enumerate(rows):
        if not Path(r["wav"]).exists():
            continue
        r["mtime"] = Path(r["wav"]).stat().st_mtime
        if (r["wav"], r["mtime"]) in cache:
            out.append(dict(cache[(r["wav"], r["mtime"])], **r))
            continue
        segs, _ = asr.transcribe(r["wav"], language="fr", beam_size=5, condition_on_previous_text=False,
                                 without_timestamps=True)
        hyp = " ".join(s.text for s in segs)
        ref = norm(texts.get(r["id"], ""))
        r = dict(r, hyp=hyp)
        if ref:
            r["words"] = len(ref.split())
            r["wer"] = jiwer.wer(ref, norm(hyp) or "∅")
            r["cer"] = jiwer.cer(ref, norm(hyp) or "∅")
        y, sr = librosa.load(r["wav"], sr=16000)
        f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=500, sr=sr)
        if voiced.any():
            r["f0"] = float(np.nanmedian(f0[voiced]))
        if r["id"].startswith("r"):
            r["pauses"] = pauses(y, sr)
            r["written_pauses"] = texts[r["id"]].count("…")
        out.append(r)
        if k % 100 == 0:
            print(k, "/", len(rows), file=sys.stderr)
    (RES / "eval.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n")
    report(meta, out, texts)


def _wer(rows):
    rows = [r for r in rows if "wer" in r]
    words = sum(r["words"] for r in rows)
    return sum(r["wer"] * r["words"] for r in rows) / words if words else float("nan")


def report(meta: dict, rows: list[dict], texts: dict) -> None:
    variants = list(dict.fromkeys(r["variant"] for r in rows))
    lines = ["| Variante | Moteur | WER phrases | WER fragments | WER réponses entières | Hallucinations | F0 médiane | "
             "Pauses rendues (réponses) | RTF |", "|" + "---|" * 9]
    details, summary = [], []
    for v in variants:
        vr = [r for r in rows if r["variant"] == v]
        seg = [r for r in vr if not r["id"].startswith("r") and r["id"] != "filler"]
        rep = [r for r in vr if r["id"].startswith("r")]
        frag = [r for r in seg if r.get("words", 0) <= 3]
        full = [r for r in seg if r.get("words", 0) > 3]
        base = seg + rep
        pace = st.median(r["dur_s"] / max(1, len(texts[r["id"]])) for r in base) if base else 0
        halluc = [r for r in base if r["dur_s"] > 2.5 * pace * len(texts[r["id"]]) + 0.8
                  or (r.get("words", 0) >= 4 and r.get("wer", 0) >= 0.5)]
        f0s = [r["f0"] for r in base if "f0" in r]
        written = sum(r.get("written_pauses", 0) for r in rep)
        rendered = sum(min(r.get("pauses", 0), r.get("written_pauses", 0)) for r in rep)
        rtf = sum(r["synth_s"] for r in base) / max(1e-9, sum(r["dur_s"] for r in base))
        row = {"variant": v, "engine": vr[0]["engine"], "wer_full": _wer(full), "wer_frag": _wer(frag),
               "wer_replies": _wer(rep), "halluc": len(halluc), "n": len(base), "f0": st.median(f0s) if f0s else None,
               "pauses": f"{rendered}/{written}" if rep else "—", "rtf": rtf}
        summary.append(row)
        f0 = f"{row['f0']:.0f} Hz" if row["f0"] else "—"
        lines.append(f"| {v} | {row['engine']} | {row['wer_full']:.1%} | {row['wer_frag']:.1%} | {row['wer_replies']:.1%} | "
                     f"{len(halluc)} / {len(base)} | {f0} | {row['pauses']} | {rtf:.2f} |")
        for r in halluc[:6]:
            details.append(f"- `{v}` {r['id']} « {texts[r['id']]} » → « {r['hyp'].strip()} » ({r['dur_s']:.1f} s)")
    engines = ["| Moteur | Modèle | Licence | Chargement | Mémoire GPU | Déterministe | Fréquence |", "|---|---|---|---|---|---|---|"]
    for e, m in meta.items():
        engines.append(f"| {e} | {m.get('model', '')} | {m.get('licence', '')} | {m.get('load_s')} s | {m.get('peak_gpu_gb')} Go | "
                       f"{'oui' if m.get('deterministic') else 'non'} | {m.get('sample_rate')} Hz |")
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    text = "\n".join(["# Criblage voix v2 — résultats objectifs", "",
                      "WER : Whisper large-v3 (« euh » et « hein » retirés des deux côtés). Réponses entières : "
                      "synthétisées d'un bloc, pauses écrites « … ». F0 : un enfant de 8 ans parle vers 250–300 Hz.", "",
                      *lines, "", *engines, "", "## Segments signalés (6 au plus par variante)", "", *details, ""])
    (RES / "screening_v2.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
