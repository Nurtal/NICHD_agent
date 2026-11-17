"""N0 (rendering fidelity) and N1-auto (objective fluency proxies), on the corpus of make_corpus.py.

Runs in the VOICE env (numpy, librosa, faster-whisper), see experiments/voice_eval/README.md:

    experiments/voice_eval/run_voice_env.sh n0_fidelity.py
"""

from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

import librosa
import numpy as np
from faster_whisper import WhisperModel

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "src"))  # nichd_sim.text only (pure Python)

from checks import Check, save
from stats import quantile, spearman

from nichd_sim.text import mentions, normalize

RES = HERE / "results"
FRAME_MS = 10
MIN_SILENCE_MS = 200
PLANNED_MS = 300
RUN_PAUSE_MS = 250
FILLER = "euh…"
MIN_WORDS = 8


def load(rel: str) -> tuple[np.ndarray, int]:
    y, sr = librosa.load(RES / rel, sr=None)
    return (y * 32768).astype(np.float32), sr


def frames_rms(y: np.ndarray, sr: int) -> np.ndarray:
    n = int(sr * FRAME_MS / 1000)
    k = len(y) // n
    return np.sqrt((y[: k * n].reshape(k, n) ** 2).mean(axis=1)) if k else np.zeros(0)


def silent_frames(y: np.ndarray, sr: int) -> np.ndarray:
    rms = frames_rms(y, sr)
    thr = max(60.0, 0.02 * float(np.percentile(rms, 95))) if len(rms) else 60.0
    return rms < thr


def silences(y: np.ndarray, sr: int, min_ms: int = MIN_SILENCE_MS) -> list[tuple[int, int]]:
    """[start_ms, end_ms) of every silent run ≥ min_ms (energy below 2 % of the loud frames)."""
    sil = silent_frames(y, sr)
    out, start = [], None
    for i, s in enumerate(list(sil) + [False]):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if (i - start) * FRAME_MS >= min_ms:
                out.append((start * FRAME_MS, i * FRAME_MS))
            start = None
    return out


def overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def syllables(text: str) -> int:
    t = re.sub(r"\beuh\b", " ", normalize(text))
    return len(re.findall(r"[aeiouy]+", t))


def main() -> None:
    data = json.loads((RES / "corpus.json").read_text(encoding="utf-8"))
    replies = data["replies"]
    asr = WhisperModel("large-v3", device="cuda", compute_type="float16")

    onset_err, recall_hits, recall_n, dur_err, unplanned, hes, total_sil = [], 0, 0, [], [], [], []
    fill_ok, fill_n, aud_ok, aud_n, misses, fill_ms = 0, 0, 0, 0, [], []
    fluency = []
    for r in replies:
        y, sr = load(r["wav"])
        sil = silences(y, sr)
        speech = [i for i, s in enumerate(silent_frames(y, sr)) if not s]
        if not speech:
            continue
        first, last = speech[0] * FRAME_MS, (speech[-1] + 1) * FRAME_MS
        onset_err.append(abs(first - r["delivery"]["onset_ms"]))
        planned = [(s["start_ms"], s["end_ms"]) for s in r["timeline"]
                   if s["kind"] == "silence" and s["end_ms"] - s["start_ms"] >= PLANNED_MS]
        for p in planned:
            recall_n += 1
            best = max(sil, key=lambda m: overlap(m, p), default=None)
            if best and overlap(best, p) >= 0.5 * (p[1] - p[0]):
                recall_hits += 1
                dur_err.append(abs((best[1] - best[0]) - (p[1] - p[0])))
        unplanned.append(sum(1 for m in sil if m[1] - m[0] >= PLANNED_MS
                             and all(overlap(m, p) < 0.5 * (m[1] - m[0]) for p in planned)))
        hes.append(r["delivery"]["hesitation"])
        total_sil.append(sum(e - s for s, e in sil))
        # fillers: voiced and plausibly long
        for s in r["timeline"]:
            if s["kind"] == "speech" and s["text"] == FILLER:
                fill_n += 1
                seg = y[int(s["start_ms"] * sr / 1000): int(s["end_ms"] * sr / 1000)] / 32768
                ms = s["end_ms"] - s["start_ms"]
                if len(seg) > sr // 20:
                    _, voiced, _ = librosa.pyin(seg, fmin=120, fmax=600, sr=sr, frame_length=1024)
                    fill_ok += bool(250 <= ms <= 700 and np.mean(voiced) >= 0.5)
                fill_ms.append(ms)
        # audibility of the units said
        units = [u for u in r["units"] if u["anchors"]]
        if units:
            hyp = normalize(" ".join(s.text for s in asr.transcribe(
                librosa.resample(y / 32768, orig_sr=sr, target_sr=16000), language="fr", beam_size=5,
                without_timestamps=True, condition_on_previous_text=False)[0]))
            for u in units:
                aud_n += 1
                if any(mentions(hyp, a) for a in u["anchors"]):
                    aud_ok += 1
                else:
                    misses.append({"reply": r["id"], "unit": u["id"], "anchors": u["anchors"], "heard": hyp})
        # N1-auto: fluency within the reply (from the first to the last sound; onset excluded)
        total = (last - first) / 1000
        inner = [m for m in sil if m[0] >= first and m[1] <= last and m[1] - m[0] >= RUN_PAUSE_MS]
        voiced_s = total - sum(e - s for s, e in inner) / 1000
        fillers = sum(1 for s in r["timeline"] if s["text"] == FILLER)
        syl = syllables(r["text"]) + fillers
        if total > 0.3 and syl >= 3:
            fluency.append({"hesitation": r["delivery"]["hesitation"], "words": len(r["text"].split()),
                            "speech_rate": syl / total,
                            "mlr": syl / (len(inner) + 1), "phonation": voiced_s / total,
                            "pauses_min": len(inner) / total * 60, "fillers_min": fillers / total * 60})

    c = []
    c.append(Check("N0", "Silence initial : erreur absolue moyenne (ms)", st.fmean(onset_err), "< 30",
                   st.fmean(onset_err) < 30, f"{len(onset_err)} réponses"))
    c.append(Check("N0", "Silence initial : erreur p95 (ms)", quantile(onset_err, 0.95), "< 60",
                   quantile(onset_err, 0.95) < 60))
    rec = recall_hits / recall_n
    c.append(Check("N0", "Rappel des silences planifiés (≥ 300 ms)", rec, "≥ 0,95", rec >= 0.95, f"{recall_n} silences"))
    c.append(Check("N0", "Erreur de durée des silences retrouvés (ms)", st.fmean(dur_err), "< 50",
                   st.fmean(dur_err) < 50))
    up = st.fmean(unplanned)
    c.append(Check("N0", "Pauses non planifiées (≥ 300 ms) par réponse", up, "< 0,2", up < 0.2,
                   f"{sum(unplanned)} au total"))
    rho = spearman(hes, total_sil)
    c.append(Check("N0", "Spearman ρ : hésitation décidée ↔ silence total mesuré", rho, "≥ 0,8", rho >= 0.8))
    fr = fill_ok / fill_n if fill_n else float("nan")
    c.append(Check("N0", "« euh » voisés et de durée plausible (250–700 ms)", fr, "≥ 0,95", fr >= 0.95,
                   f"{fill_n} « euh », tous voisés ; {sum(m < 250 for m in fill_ms)} trop courts "
                   f"(min {min(fill_ms)} ms) ; contrôle acoustique, pas perceptif"))
    au = aud_ok / aud_n
    c.append(Check("N0", "Audibilité des unités (ancres retrouvées par Whisper)", au, "≥ 0,95", au >= 0.95,
                   f"{aud_n} unités"))
    c.append(Check("N0", "Déterminisme (même réponse → même audio)", sum(data["determinism"]) /
                   len(data["determinism"]), "1", all(data["determinism"])))
    # controlled rate: same text at 0.75 / 0.85 / 1.0; speed measured relative to the 1.0 render
    measured = {}
    for x in data["rate"]:
        y, sr = load(x["wav"])
        speech = [i for i, s in enumerate(silent_frames(y, sr)) if not s]
        measured[(x["text_id"], x["rate"])] = (speech[-1] - speech[0] + 1) * FRAME_MS
    errors, xs, ys = [], [], []
    for k in {x["text_id"] for x in data["rate"]}:
        base = measured[(k, 1.0)]
        for r_ in (0.75, 0.85, 1.0):
            xs.append(r_)
            ys.append(base / measured[(k, r_)])  # relative speed, 1.0 for the reference render
            if r_ != 1.0:
                errors.append(abs(measured[(k, r_)] / base - 1 / r_) / (1 / r_))
    rho_rate = spearman(xs, ys)
    c.append(Check("N0", "Débit : erreur relative de durée vs 1/débit (textes identiques)", st.fmean(errors),
                   "< 0,05", st.fmean(errors) < 0.05))
    c.append(Check("N0", "Débit : Spearman ρ (débit demandé ↔ vitesse mesurée)", rho_rate, "≥ 0,7", rho_rate >= 0.7))
    # controlled volume
    db = {}
    for x in data["volume"]:
        y, sr = load(x["wav"])
        rms = frames_rms(y, sr)
        loud = rms[~silent_frames(y, sr)]
        db[(x["text_id"], x["volume"])] = 20 * np.log10(np.sqrt(np.mean(loud ** 2)))
    texts = {x["text_id"] for x in data["volume"]}
    low = st.fmean(db[(k, "low")] - db[(k, "normal")] for k in texts)
    wh = st.fmean(db[(k, "whisper")] - db[(k, "normal")] for k in texts)
    c.append(Check("N0", "Volume « bas » vs normal (dB)", float(low), "−4,4 ± 1", abs(low + 4.44) <= 1))
    c.append(Check("N0", "Volume « chuchoté » vs normal (dB)", float(wh), "−9,1 ± 1", abs(wh + 9.12) <= 1))
    save("n0", c, {"audibility_misses": misses[:40]})

    # N1-auto. Fluency proxies are defined for running speech: thresholds apply to replies of
    # ≥ MIN_WORDS words (internal pauses are possible: one per 4 words at most). Short replies show
    # hesitation through the initial silence only, measured in N0. All-replies values are reported.
    running = [f for f in fluency if f["words"] >= MIN_WORDS]
    h = [f["hesitation"] for f in running]
    n1 = []
    for key, label, target, ok in (
        ("speech_rate", "Débit (syllabes/s, pauses comprises) ↔ hésitation", "ρ ≤ −0,7", lambda r: r <= -0.7),
        ("mlr", "Longueur moyenne des segments de parole ↔ hésitation", "ρ ≤ −0,6", lambda r: r <= -0.6),
        ("phonation", "Proportion de temps de parole ↔ hésitation", "ρ ≤ −0,7", lambda r: r <= -0.7),
        ("pauses_min", "Pauses silencieuses par minute ↔ hésitation", "ρ > 0", lambda r: r > 0),
        ("fillers_min", "« euh » par minute ↔ hésitation", "ρ > 0", lambda r: r > 0),
    ):
        rho = spearman(h, [f[key] for f in running])
        rho_all = spearman([f["hesitation"] for f in fluency], [f[key] for f in fluency])
        n1.append(Check("N1-auto", label, rho, target, ok(rho),
                        f"{len(running)} réponses ≥ {MIN_WORDS} mots ; toutes ({len(fluency)}) : ρ = {rho_all:.2f}"))
    save("n1auto", n1)


if __name__ == "__main__":
    main()
