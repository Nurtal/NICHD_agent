"""Score the ablation transcripts with the same text detectors for both conditions.

    uv run python experiments/ablation/analyze.py [results/transcripts.jsonl] [-o report.md]
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from protocol import PLANS, ROLES, accepts_suggestion, has_keyword, is_dont_know, units_mentioned  # noqa: E402

from nichd_sim.evaluation import load_scenarios  # noqa: E402
from nichd_sim.output_filter import load_lexicon  # noqa: E402
from nichd_sim.text import contains, normalize  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONDS = ("hybrid", "llm_only")
LABEL = {"hybrid": "Hybride", "llm_only": "100 % LLM"}


def score(rec, scenario, lexicon):
    plan = PLANS[scenario.id]
    turns = {t["turn"]: t for t in rec["turns"]}
    said = {i: units_mentioned(scenario, t["child"]) for i, t in turns.items()}
    words = {i: len(t["child"].split()) for i, t in turns.items()}
    role = {i: ROLES[i] for i in turns}
    m = {}
    pre = [i for i in turns if role[i] in ("rapport", "rule", "practice")
           and units_mentioned(scenario, turns[i]["child"], central_only=True)]
    m["premature_disclosure"] = bool(pre)
    first = min((i for i in turns if units_mentioned(scenario, turns[i]["child"], central_only=True)), default=None)
    m["first_disclosure_turn"] = first
    m["rule_turn_words"] = st.mean(words[i] for i in (3, 4))
    # directives: the targeted fact is given; other facts volunteered on top
    hits, extras = [], []
    for i, key in ((12, 0), (13, 1), (16, 2), (19, 0)):
        target = plan.directives[key][0]
        hits.append(target in said[i])
        extras.append(len(said[i] - {target}))
    m["directive_hit"] = st.mean(hits)
    m["directive_extra_units"] = st.mean(extras)
    m["repeat_consistent"] = hits[0] == hits[3]
    m["out_dont_know"] = st.mean(is_dont_know(turns[i]["child"]) for i in (14, 17))
    accepted = []
    for i, (_, kws) in ((15, plan.false_suggestions[0]), (18, plan.false_suggestions[1])):
        accepted.append(accepts_suggestion(turns[i]["child"], kws))
    m["suggestion_accepted"] = st.mean(accepted)
    recall_text = " ".join(turns[i]["child"] for i in (20, 21))
    rep = [has_keyword(recall_text, plan.false_suggestions[k][1]) for k, a in enumerate(accepted) if a]
    m["_accepted_n"], m["_repeated_n"] = len(rep), sum(rep)
    m["invitation_words"] = st.mean(words[i] for i in (9, 11, 20))
    m["invitation_units"] = st.mean(len(said[i]) for i in (9, 11, 20))
    norm_all = [normalize(t["child"]) for t in turns.values()]
    m["forbidden_hits"] = sum(any(contains(n, w) for w in lexicon) for n in norm_all)
    m["empty"] = sum(not t["child"].strip() for t in turns.values())
    m["fallbacks"] = sum(t.get("fallback", False) for t in turns.values())
    m["latency_s"] = st.mean(t["latency_s"] for t in turns.values())
    return m


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2
            i = j + 1
        return r
    try:
        return st.correlation(ranks(xs), ranks(ys))
    except st.StatisticsError:
        return float("nan")


def pct(x):
    return f"{100 * x:.0f} %"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=str(ROOT / "experiments/ablation/results/transcripts.jsonl"))
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    scenarios = load_scenarios(ROOT / "scenarios")
    lexicon = load_lexicon()
    rows = defaultdict(list)  # (cond, scenario) -> metrics
    model = None
    for line in Path(args.path).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        model = rec["model"]
        rows[(rec["condition"], rec["scenario"])].append(score(rec, scenarios[rec["scenario"]], lexicon))

    def agg(cond, key, sids=None, f=st.mean):
        vals = [m[key] for (c, s), ms in rows.items() if c == cond and (sids is None or s in sids) for m in ms
                if m[key] is not None]
        return f(vals) if vals else float("nan")

    n = {c: sum(len(ms) for (cc, _), ms in rows.items() if cc == c) for c in CONDS}
    out = [f"# Ablation : enfant hybride vs enfant 100 % LLM\n",
           f"Modèle : `{model}` (local, Ollama), température 0,7, réflexion désactivée. "
           f"{n['hybrid']} entretiens par condition (7 scénarios × {n['hybrid'] // 7} graines), 23 tours scriptés "
           "identiques. La condition hybride reçoit les étiquettes NICHD de référence (classifieur hors comparaison) ; "
           "la condition 100 % LLM reçoit la fiche complète, le profil, des consignes de comportement et tout "
           "l'historique. Mêmes détecteurs textuels (ancres des unités) pour les deux.\n",
           "## Résultats globaux\n",
           "| Critère (attendu) | " + " | ".join(LABEL[c] for c in CONDS) + " |", "|---|---|---|"]

    def line(label, key, fmt=pct, f=st.mean):
        out.append(f"| {label} | " + " | ".join(fmt(agg(c, key, f=f)) for c in CONDS) + " |")

    line("Entretiens où un fait central sort avant la transition (attendu : 0)", "premature_disclosure")
    line("Mots par réponse aux règles de base (attendu : très court)", "rule_turn_words", fmt=lambda x: f"{x:.1f}")
    line("Question directive : fait ciblé donné", "directive_hit")
    line("Question directive : autres faits ajoutés (attendu : ~0)", "directive_extra_units", fmt=lambda x: f"{x:.2f}")
    line("Même question directive répétée : réponse cohérente", "repeat_consistent")
    line("Question hors scénario : « je sais pas »", "out_dont_know")
    line("Suggestion fausse acceptée", "suggestion_accepted")
    acc = {c: agg(c, "_accepted_n", f=sum) for c in CONDS}
    reps = {c: agg(c, "_repeated_n", f=sum) for c in CONDS}
    out.append("| Faux détail accepté puis repris au rappel libre | " + " | ".join(
        f"{int(reps[c])}/{int(acc[c])}" for c in CONDS) + " |")
    line("Réponses contenant un terme du lexique interdit (total)", "forbidden_hits", fmt=lambda x: f"{int(x)}", f=sum)
    line("Réponses vides (total)", "empty", fmt=lambda x: f"{int(x)}", f=sum)
    line("Latence moyenne par tour", "latency_s", fmt=lambda x: f"{x:.1f} s")
    out.append(f"\nRéponses de repli de la condition hybride (filtre de sortie) : {int(agg('hybrid', 'fallbacks', f=sum))}.\n")

    out += ["## Le profil de l'enfant est-il respecté ?\n",
            "Corrélation de Spearman sur les 7 scénarios (n = 7, indicatif) entre un paramètre du profil et le "
            "comportement observé.\n",
            "| Scénario | Âge | Réticence | Suggestibilité | " + " | ".join(
                f"1er fait (tour) {LABEL[c]} | Suggestions acceptées {LABEL[c]} | Mots / invitation {LABEL[c]}" for c in CONDS) + " |",
            "|---|---|---|---|" + "---|---|---|" * len(CONDS)]
    sids = sorted(scenarios)
    per = {c: {s: {} for s in sids} for c in CONDS}
    for c in CONDS:
        for s in sids:
            for key in ("first_disclosure_turn", "suggestion_accepted", "invitation_words"):
                per[c][s][key] = agg(c, key, {s})
    for s in sids:
        p = scenarios[s].child_profile
        cells = []
        for c in CONDS:
            cells += [f"{per[c][s]['first_disclosure_turn']:.1f}", pct(per[c][s]["suggestion_accepted"]),
                      f"{per[c][s]['invitation_words']:.0f}"]
        out.append(f"| {s} | {p.age} | {p.reluctance} | {p.suggestibility} | " + " | ".join(cells) + " |")
    prof = [scenarios[s].child_profile for s in sids]
    out += ["", "| Lien attendu | " + " | ".join(LABEL[c] for c in CONDS) + " |", "|---|---|---|"]
    for label, xs, key in (
        ("Réticence ↗ → dévoilement plus tardif (ρ > 0)", [p.reluctance for p in prof], "first_disclosure_turn"),
        ("Suggestibilité ↗ → plus d'acceptations (ρ > 0)", [p.suggestibility for p in prof], "suggestion_accepted"),
        ("Âge ↗ → récits plus longs (ρ > 0)", [p.age for p in prof], "invitation_words"),
    ):
        out.append(f"| {label} | " + " | ".join(
            f"{spearman(xs, [per[c][s][key] for s in sids]):+.2f}" for c in CONDS) + " |")
    text = "\n".join(out) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
