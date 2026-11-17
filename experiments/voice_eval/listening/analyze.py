"""N1 — Analysis of the blind listening test.

    uv run python experiments/voice_eval/listening/analyze.py [ratings_dir]

Reads every ecoute_*.json exported by rate.html (default: listening/ratings/) and the hidden
design (listening/pack/design.json). With few listeners, rely on the confidence intervals.
"""

from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from checks import Check, save
from stats import proportion_ci, spearman


def icc_2_1(matrix: list[list[float]]) -> float:
    """ICC(2,1): two-way random effects, absolute agreement, single rater (clips × raters, complete)."""
    n, k = len(matrix), len(matrix[0])
    grand = st.fmean(v for row in matrix for v in row)
    rows = [st.fmean(r) for r in matrix]
    cols = [st.fmean(matrix[i][j] for i in range(n)) for j in range(k)]
    ssr = k * sum((m - grand) ** 2 for m in rows)
    ssc = n * sum((m - grand) ** 2 for m in cols)
    sst = sum((v - grand) ** 2 for row in matrix for v in row)
    sse = sst - ssr - ssc
    msr, msc, mse = ssr / (n - 1), ssc / (k - 1), sse / ((n - 1) * (k - 1))
    return (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)


def analyze(ratings: list[dict], design: dict) -> list[Check]:
    clips = {c["id"]: c for c in design["clips"]}
    pairs = [t for t in design["tasks"] if t["kind"] == "pair"]
    by_clip: dict[str, list[dict]] = {}
    pair_ok = pair_n = 0
    for listener in ratings:
        for a in listener["answers"]:
            if "pair" in a:
                task = next(t for t in pairs if sorted(t["clips"]) == sorted(a["clips"]))
                pair_n += 1
                pair_ok += a["pair"] == task["more_hesitant"]
            else:
                by_clip.setdefault(a["clips"][0], []).append({**a, "listener": listener["listener"]})
    checks = []
    n_listeners = len(ratings)
    note = f"{n_listeners} auditeur(s)"
    # perceived vs decided hesitation (all rated clips)
    decided, perceived = [], []
    for cid, ans in by_clip.items():
        decided.append(clips[cid]["hesitation"])
        perceived.append(st.fmean(float(a["hesitation"]) for a in ans))
    rho = spearman(decided, perceived)
    checks.append(Check("N1", "Hésitation perçue ↔ décidée (Spearman ρ, moyenne par extrait)", rho, "≥ 0,6",
                        rho >= 0.6, note))
    lo, hi = proportion_ci(pair_ok, pair_n)
    checks.append(Check("N1", "Paires : l'extrait le plus hésitant est reconnu", pair_ok / pair_n if pair_n else float("nan"),
                        "≥ 0,80", pair_n > 0 and pair_ok / pair_n >= 0.80, f"IC 95 % [{lo:.2f} ; {hi:.2f}] ; {pair_n} jugements"))
    # lie: accuracy should be at chance (CI contains 0.5)
    lie_answers = [(clips[cid]["lie"], a["lie"] == "oui") for cid, ans in by_clip.items()
                   if clips[cid]["block"] == "lie" for a in ans]
    ok = sum(truth == said for truth, said in lie_answers)
    lo, hi = proportion_ci(ok, len(lie_answers))
    # At chance is only meaningful if the same listeners DO hear hesitation (inattentive listeners are
    # at chance too): the check requires the perception check above to pass.
    attentive = rho >= 0.6
    checks.append(Check("N1", "Mensonge reconnu à la voix seule (même texte, diction du mensonge vs de la vérité)",
                        ok / len(lie_answers) if lie_answers else float("nan"),
                        "IC 95 % contient 0,5, auditeurs attentifs (ρ ≥ 0,6)",
                        bool(lie_answers) and lo <= 0.5 <= hi and attentive,
                        f"IC 95 % [{lo:.2f} ; {hi:.2f}] ; {len(lie_answers)} jugements"
                        + ("" if attentive else " ; non interprétable : l'hésitation n'est pas perçue")))
    # naturalness: with delivery vs child voice without delivery
    def mos(sel):
        xs = [float(a["naturalness"]) for cid, ans in by_clip.items() if sel(clips[cid]) for a in ans]
        return st.fmean(xs) if xs else float("nan")
    with_d = mos(lambda c: c["block"] == "gradient" and c["level"] > 0)
    without = mos(lambda c: c.get("voice") == "enfant sans diction")
    checks.append(Check("N1", "Naturel (MOS) : avec diction / sans diction", f"{with_d:.2f} / {without:.2f}",
                        "avec ≥ sans, et ≥ 3", with_d >= without and with_d >= 3, note))
    ages = [float(a["age"]) for cid, ans in by_clip.items() if clips[cid].get("voice") != "adulte" for a in ans]
    med_age = st.median(ages) if ages else float("nan")
    q1, _, q3 = st.quantiles(ages, n=4) if len(ages) >= 4 else (float("nan"),) * 3
    checks.append(Check("N1", "Âge perçu de la voix d'enfant (médiane, années)", med_age, "6–11, écart interquartile dans 5–12",
                        6 <= med_age <= 11 and 5 <= q1 and q3 <= 12, f"{note} ; écart interquartile [{q1:.0f} ; {q3:.0f}]"))
    full = [cid for cid, ans in by_clip.items() if len({a["listener"] for a in ans}) == n_listeners]
    if n_listeners >= 2 and len(full) >= 5:
        matrix = [[float(next(a["hesitation"] for a in by_clip[cid] if a["listener"] == r["listener"]))
                   for r in ratings] for cid in full]
        icc = icc_2_1(matrix)
        checks.append(Check("N1", "Accord inter-auditeurs sur l'hésitation (ICC(2,1))", icc, "≥ 0,6 (indicatif)",
                            None if n_listeners < 10 else icc >= 0.6, note))
    causes = {}
    for cid, ans in by_clip.items():
        if clips[cid]["block"] == "causes":
            causes.setdefault(clips[cid]["cause"], []).extend(float(a["hesitation"]) for a in ans)
    checks.append(Check("N1", "Hésitation perçue par cause, à hésitation décidée comparable",
                        " ; ".join(f"{k} {st.fmean(v):.2f}" for k, v in sorted(causes.items())), "rapporté", None, note))
    return checks


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "ratings"
    ratings = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("ecoute_*.json"))]
    if not ratings:
        sys.exit(f"aucune réponse dans {folder}")
    design = json.loads((HERE / "pack" / "design.json").read_text(encoding="utf-8"))
    save("n1", analyze(ratings, design))


if __name__ == "__main__":
    main()
