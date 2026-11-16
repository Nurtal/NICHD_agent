"""Objective comparison of the TTS variants (run with the kokoro env, see README).

- intelligibility: Whisper large-v3 transcribes each segment → WER / CER against the text
  (« euh » removed on both sides), separately for fragments (≤ 3 words) and full sentences;
- median pitch (pYIN): an 8-year-old speaks around 250–300 Hz, an adult woman ~200 Hz;
- speed control: duration at rate 0.75 / duration at rate 1.0 (expected 1.33);
- hallucinations: segment far longer than the variant's usual pace, or mostly misheard;
- latency: synthesis time per segment and real-time factor; GPU memory; determinism.
"""

from __future__ import annotations

import json
import re
import statistics as st
import unicodedata
from pathlib import Path

import jiwer
import librosa
import numpy as np
from faster_whisper import WhisperModel

HERE = Path(__file__).parent
RES = HERE / "results"
AUDIO = RES / "audio"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text.replace("’", "'").lower())
    text = re.sub(r"\beuh+\b", " ", text)
    text = re.sub(r"[^\w' -]", " ", text).replace("-", " ")
    return " ".join(text.split())


def load_synth() -> tuple[dict, list[dict]]:
    meta, rows = {}, []
    for path in sorted(RES.glob("synth_*.jsonl")):
        lines = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
        meta[lines[0]["engine"]] = lines[0]
        rows += lines[1:]
    return meta, rows


def main() -> None:
    corpus = {c["id"]: c["text"] for c in json.loads((RES / "corpus.json").read_text(encoding="utf-8"))}
    meta, rows = load_synth()
    try:
        asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:  # cuDNN not found: CPU is slower but fine for ~400 short segments
        asr = WhisperModel("large-v3", device="cpu", compute_type="int8")
    by_key = {(r["variant"], r["rate"], r["id"]): r for r in rows}
    out_rows = []
    for r in rows:
        folder = r["variant"] if r["rate"] == 1.0 else f"{r['variant']}@{r['rate']}"
        wav = AUDIO / folder / f"{r['id']}.wav"
        segments, _ = asr.transcribe(str(wav), language="fr", beam_size=5, condition_on_previous_text=False,
                                     without_timestamps=True)
        hyp = " ".join(s.text for s in segments)
        r = dict(r, hyp=hyp)
        ref = norm(corpus[r["id"]])
        if ref:
            r["words"] = len(ref.split())
            r["wer"] = jiwer.wer(ref, norm(hyp) or "∅")
            r["cer"] = jiwer.cer(ref, norm(hyp) or "∅")
        if r["rate"] == 1.0:
            y, sr = librosa.load(wav, sr=16000)
            f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=500, sr=sr)
            if voiced.any():
                r["f0"] = float(np.nanmedian(f0[voiced]))
        else:
            base = by_key.get((r["variant"], 1.0, r["id"]))
            if base:
                r["stretch"] = r["dur_s"] / base["dur_s"]
        out_rows.append(r)
    (RES / "eval.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + "\n")
    report(meta, out_rows, corpus)


def _wer(rows):
    """Corpus-level WER: total errors / total reference words."""
    rows = [r for r in rows if "wer" in r]
    words = sum(r["words"] for r in rows)
    return sum(r["wer"] * r["words"] for r in rows) / words if words else float("nan")


def report(meta: dict, rows: list[dict], corpus: dict) -> None:
    variants = list(dict.fromkeys(r["variant"] for r in rows))
    lines = ["| Variante | WER phrases | WER fragments (≤ 3 mots) | CER | F0 médiane | Débit 0,75 (attendu 1,33) | "
             "Hallucinations | Synthèse / segment | RTF |", "|" + "---|" * 9]
    details = []
    for v in variants:
        base = [r for r in rows if r["variant"] == v and r["rate"] == 1.0 and r["id"] != "filler"]
        frag = [r for r in base if r.get("words", 0) <= 3]
        full = [r for r in base if r.get("words", 0) > 3]
        cer = st.mean(r["cer"] for r in base if "cer" in r)
        f0 = st.median(r["f0"] for r in base if "f0" in r)
        stretch = [r["stretch"] for r in rows if r["variant"] == v and "stretch" in r]
        pace = st.median(r["dur_s"] / max(1, len(corpus[r["id"]])) for r in base)
        halluc = [r for r in base if r["dur_s"] > 2.5 * pace * len(corpus[r["id"]]) + 0.5
                  or (r.get("words", 0) >= 4 and r["wer"] >= 0.5)]
        synth = st.median(r["synth_s"] for r in base)
        rtf = sum(r["synth_s"] for r in base) / sum(r["dur_s"] for r in base)
        lines.append(f"| {v} | {_wer(full):.1%} | {_wer(frag):.1%} | {cer:.1%} | {f0:.0f} Hz | "
                     f"{st.mean(stretch):.2f} | {len(halluc)} / {len(base)} | {synth:.2f} s | {rtf:.2f} |")
        for r in halluc:
            details.append(f"- `{v}` {r['id']} « {corpus[r['id']]} » → « {r['hyp'].strip()} » ({r['dur_s']:.1f} s)")
        filler = next((r for r in rows if r["variant"] == v and r["id"] == "filler" and r["rate"] == 1.0), None)
        if filler:
            details.append(f"- `{v}` « euh… » : {filler['dur_s']:.2f} s, entendu « {filler['hyp'].strip()} »")
    engines = ["| Moteur | Chargement | Mémoire GPU (pic) | Déterministe (seed fixée) | Fréquence |", "|---|---|---|---|---|"]
    for e, m in meta.items():
        engines.append(f"| {e} | {m['load_s']} s | {m['peak_gpu_gb']} Go | {'oui' if m['deterministic'] else 'non'} | "
                       f"{m['sample_rate']} Hz |")
    text = "\n".join(["# Criblage TTS — résultats bruts", "", *lines, "", *engines, "",
                      "## Segments signalés et « euh »", "", *details, ""])
    (RES / "screening.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
