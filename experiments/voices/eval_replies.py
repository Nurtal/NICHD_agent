"""Fragment fix check, step 2 (kokoro env): Whisper on whole replies and on each « euh »."""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import jiwer
import librosa
from evaluate import norm
from faster_whisper import WhisperModel

OUT = Path(__file__).parent / "results" / "replies"


def main() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    rows = []
    for m in manifest:
        y, sr = librosa.load(OUT / m["wav"], sr=16000)
        hyp = " ".join(s.text for s in asr.transcribe(y, language="fr", beam_size=5, without_timestamps=True,
                                                      condition_on_previous_text=False)[0])
        ref = norm(m["text"])
        fillers = []
        for sp in m["spans"]:
            if sp["kind"] == "speech" and sp["text"] == "euh…":
                seg = y[int(sp["start_ms"] * 16):int(sp["end_ms"] * 16)]
                heard = " ".join(s.text for s in asr.transcribe(seg, language="fr", beam_size=5,
                                                                without_timestamps=True)[0]).strip()
                fillers.append({"ms": sp["end_ms"] - sp["start_ms"], "heard": heard})
        rows.append({**m, "hyp": hyp, "words": len(ref.split()), "wer": jiwer.wer(ref, norm(hyp) or "∅"),
                     "starts_with_et": norm(hyp).startswith("et ") and not ref.startswith("et "),
                     "fillers": fillers})
    (OUT / "eval.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    lines = ["| Mode | Réponses | WER (réponse entière) | Réponses parfaites | « Et » parasite en tête | "
             "« euh » entendus comme euh/heu | Durée médiane d'un « euh » |", "|---|---|---|---|---|---|---|"]
    for mode in ("per-piece", "utterance"):
        rs = [r for r in rows if r["mode"] == mode]
        wer = sum(r["wer"] * r["words"] for r in rs) / sum(r["words"] for r in rs)
        fl = [f for r in rs for f in r["fillers"]]
        ok = sum(norm(f["heard"]) in ("euh", "heu", "heuh", "euhh", "hum", "hmm") for f in fl)
        lines.append(f"| {mode} | {len(rs)} | {wer:.1%} | {sum(r['wer'] == 0 for r in rs)} | "
                     f"{sum(r['starts_with_et'] for r in rs)} | {ok} / {len(fl)} | "
                     f"{st.median(f['ms'] for f in fl) if fl else 0:.0f} ms |")
    text = "\n".join(["# Fragments : une synthèse par fragment vs une synthèse par réponse", "", *lines, ""])
    (OUT / "report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
