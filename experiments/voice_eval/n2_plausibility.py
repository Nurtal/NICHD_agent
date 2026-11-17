"""N2 — Plausibility of the simulated behaviour (decisions only, no audio).

    uv run python experiments/voice_eval/n2_plausibility.py [--seeds 5]
"""

from __future__ import annotations

import argparse
import statistics as st

from checks import Check, save
from lie_pairs import pairs
from sim import corpus
from stats import auc, cohen_d, mann_whitney_p, quantile

from nichd_sim.delivery import HesitationCause
from nichd_sim.engine import SpeechAct

FILLER_MS = 400
"""Typical duration of a rendered « euh » (voice screening), to fold fillers into audible time."""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    replies = corpus(range(args.seeds))
    ds = [r.decision for r in replies]
    onset = lambda xs: [d.delivery.onset_ms for d in xs]
    checks: list[Check] = []

    # 1. Onset ordering: small talk < factual answer < reluctance
    by_act = {a: [d for d in ds if d.speech_act == a] for a in (SpeechAct.SMALL_TALK, SpeechAct.ANSWER,
                                                                SpeechAct.RELUCTANT)}
    means = {a: st.fmean(onset(v)) for a, v in by_act.items()}
    p1 = mann_whitney_p(onset(by_act[SpeechAct.ANSWER]), onset(by_act[SpeechAct.SMALL_TALK]))
    p2 = mann_whitney_p(onset(by_act[SpeechAct.RELUCTANT]), onset(by_act[SpeechAct.ANSWER]))
    ordered = means[SpeechAct.SMALL_TALK] < means[SpeechAct.ANSWER] < means[SpeechAct.RELUCTANT]
    checks.append(Check("N2", "Silence initial moyen : bavardage < réponse < réticence (ms)",
                        " < ".join(f"{means[a]:.0f}" for a in by_act), "ordre respecté, p < 0,01",
                        ordered and p1 < 0.01 and p2 < 0.01, f"p = {p1:.1g} ; {p2:.1g}"))

    # 2. Age effect on retrieval load (answers with true units)
    ret = {}
    for band in ("4_6", "7_9", "10_12"):
        xs = [r.decision.delivery.loads.get(HesitationCause.RETRIEVAL, 0) for r in replies
              if r.age_band == band and r.decision.speech_act == SpeechAct.ANSWER and r.decision.lie is None]
        ret[band] = st.fmean(xs) if xs else float("nan")
    checks.append(Check("N2", "Charge de récupération moyenne 4–6 > 7–9 > 10–12",
                        " > ".join(f"{v:.2f}" for v in ret.values()), "ordre respecté",
                        ret["4_6"] > ret["7_9"] > ret["10_12"]))

    # 3. Lie vs truth, other things equal: controlled pairs (same session, same question about the
    #    same protected fact; only the will to conceal differs). Observable cues only.
    ps = pairs(range(args.seeds * 5))
    lies, truths = [p[1] for p in ps], [p[2] for p in ps]
    audible = lambda xs: [d.delivery.onset_ms + sum(d.delivery.pauses_ms) + FILLER_MS * d.delivery.fillers
                          for d in xs]
    d_on, a_on = cohen_d(onset(lies), onset(truths)), auc(onset(lies), onset(truths))
    d_au, a_au = cohen_d(audible(lies), audible(truths)), auc(audible(lies), audible(truths))
    checks.append(Check("N2", "Mensonge vs vérité (paires contrôlées) : d de Cohen, silence initial", d_on,
                        "0,1 ≤ d ≤ 0,5", 0.1 <= d_on <= 0.5, f"{len(ps)} paires"))
    checks.append(Check("N2", "AUC « détecteur de mensonge » sur le silence initial", a_on, "0,55 ≤ AUC ≤ 0,65",
                        0.55 <= a_on <= 0.65))
    checks.append(Check("N2", "d de Cohen, tous indices audibles (silences + « euh »)", d_au, "0,1 ≤ d ≤ 0,5",
                        0.1 <= d_au <= 0.5))
    checks.append(Check("N2", "AUC « détecteur de mensonge » sur tous les indices audibles", a_au,
                        "0,55 ≤ AUC ≤ 0,65", 0.55 <= a_au <= 0.65))
    by_q = {q: auc(audible([p[1] for p in ps if p[0] == q]), audible([p[2] for p in ps if p[0] == q]))
            for q in ("directive", "option_posing", "suggestive")}

    # 4. Onset range
    all_on = onset(ds)
    med, p95 = st.median(all_on), quantile(all_on, 0.95)
    checks.append(Check("N2", "Silence initial : médiane (ms)", med, "500–2000", 500 <= med <= 2000))
    checks.append(Check("N2", "Silence initial : p95 (ms)", p95, "< 5000", p95 < 5000))

    # 5. Share of lies among strong hesitations
    strong = [d for d in ds if d.delivery.hesitation >= 0.6]
    lying = [d for d in strong if d.lie is not None or d.withheld]
    dominant = [d for d in strong if d.delivery.dominant_cause == HesitationCause.DECEPTION]
    share = len(lying) / len(strong) if strong else 0.0
    checks.append(Check("N2", "Part des mensonges (dont omissions) parmi les hésitations fortes (≥ 0,6)", share,
                        "< 0,40", share < 0.40, f"{len(strong)} hésitations fortes ; mensonge cause dominante : "
                        f"{len(dominant) / len(strong):.0%}" if strong else ""))
    # Restricted to deception scenarios, where lies are possible at all
    strong8 = [r.decision for r in replies if r.scenario.startswith("s08") and r.decision.delivery.hesitation >= 0.6]
    share8 = sum(d.lie is not None or bool(d.withheld) for d in strong8) / len(strong8) if strong8 else 0.0
    checks.append(Check("N2", "… dans les seuls scénarios avec mensonge (s08 et variantes)", share8, "< 0,40",
                        share8 < 0.40, f"{len(strong8)} hésitations fortes"))

    acts = {str(a): len([d for d in ds if d.speech_act == a]) for a in SpeechAct}
    save("n2", checks, {"replies": len(replies), "acts": acts, "lie_auc_by_question": by_q,
                        "onset_by_act": {str(a): means[a] for a in means}, "retrieval_by_band": ret})



if __name__ == "__main__":
    main()
