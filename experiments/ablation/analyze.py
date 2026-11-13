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

from protocol import PLANS, ROLES, accepts_suggestion, expected_acceptance, has_keyword, is_dont_know, units_mentioned  # noqa: E402

from nichd_sim.evaluation import load_scenarios  # noqa: E402
from nichd_sim.output_filter import load_lexicon  # noqa: E402
from nichd_sim.text import contains, normalize  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONDS = ("hybrid", "llm_only", "llm_only_strong")
LABEL = {"hybrid": "Hybride", "llm_only": "100 % LLM", "llm_only_strong": "100 % LLM renforcé"}


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
    productive = [i for i in (9, 11, 20, 21) if said[i]]  # invitations where the child actually tells facts
    m["productive_invitation_words"] = st.mean(words[i] for i in productive) if productive else None
    m["productive_invitation_units"] = st.mean(len(said[i]) for i in productive) if productive else None
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
    rows = defaultdict(list)  # (model, cond, scenario) -> metrics
    for line in Path(args.path).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        rows[(rec["model"], rec["condition"], rec["scenario"])].append(score(rec, scenarios[rec["scenario"]], lexicon))
    models = sorted({k[0] for k in rows}, key=lambda m: (m != "qwen3.8:latest", m))
    conds = [c for c in CONDS if any(k[1] == c for k in rows)]
    sids = sorted(scenarios)
    prof = [scenarios[s].child_profile for s in sids]
    target = {s: expected_acceptance(scenarios[s]) for s in sids}

    def agg(model, cond, key, sids_=None, f=st.mean):
        vals = [m[key] for (mo, c, s), ms in rows.items() if mo == model and c == cond
                and (sids_ is None or s in sids_) for m in ms if m[key] is not None]
        return f(vals) if vals else float("nan")

    def per_scenario(model, cond, key):
        return [agg(model, cond, key, {s}) for s in sids]

    def rho(model, cond, xs, key):
        return spearman(xs, per_scenario(model, cond, key))

    def calib_error(model, cond):
        obs = per_scenario(model, cond, "suggestion_accepted")
        return st.mean(abs(o - target[s]) for o, s in zip(obs, sids))

    derived = {
        "rho_reluctance": lambda m, c: rho(m, c, [p.reluctance for p in prof], "first_disclosure_turn"),
        "rho_suggestibility": lambda m, c: rho(m, c, [p.suggestibility for p in prof], "suggestion_accepted"),
        "rho_age": lambda m, c: rho(m, c, [p.age for p in prof], "productive_invitation_words"),
        "rho_age_units": lambda m, c: rho(m, c, [p.age for p in prof], "productive_invitation_units"),
        "calib_error": calib_error,
    }

    def value(m, c, key, f=st.mean):
        return derived[key](m, c) if key in derived else agg(m, c, key, f=f)

    n_int = {c: sum(len(ms) for (mo, cc, _), ms in rows.items() if cc == c) for c in conds}
    out = [
        "# Ablation v2 : enfant hybride vs enfant 100 % LLM, plusieurs modèles locaux\n",
        f"Modèles (Ollama, locaux) : {', '.join(f'`{m}`' for m in models)}. Température 0,7, réflexion désactivée. "
        f"Entretiens par condition : {', '.join(f'{LABEL[c]} {n_int[c]}' for c in conds)} "
        "(7 scénarios × 3 graines × modèles), 23 tours scriptés identiques. Mêmes détecteurs pour toutes les conditions.\n",
        "## Synthèse (moyenne sur les modèles, [min – max])\n",
        "| Critère (attendu) | " + " | ".join(LABEL[c] for c in conds) + " |",
        "|---|" + "---|" * len(conds),
    ]
    CRITERIA = [
        ("Entretiens où un fait central sort avant la transition (0 %)", "premature_disclosure", pct, st.mean),
        ("Mots par réponse aux règles de base (très peu)", "rule_turn_words", lambda x: f"{x:.1f}", st.mean),
        ("Directive : fait ciblé donné", "directive_hit", pct, st.mean),
        ("Directive : autres faits ajoutés (~0)", "directive_extra_units", lambda x: f"{x:.2f}", st.mean),
        ("Hors scénario : « je sais pas »", "out_dont_know", pct, st.mean),
        ("Suggestion fausse acceptée", "suggestion_accepted", pct, st.mean),
        ("Écart moyen au taux d'acceptation visé par profil (0)", "calib_error", pct, None),
        ("ρ réticence → dévoilement tardif (> 0)", "rho_reluctance", lambda x: f"{x:+.2f}", None),
        ("ρ suggestibilité → acceptations (> 0)", "rho_suggestibility", lambda x: f"{x:+.2f}", None),
        ("ρ âge → mots par récit (> 0)", "rho_age", lambda x: f"{x:+.2f}", None),
        ("ρ âge → faits par récit (> 0)", "rho_age_units", lambda x: f"{x:+.2f}", None),
        ("Latence moyenne par tour", "latency_s", lambda x: f"{x:.1f} s", st.mean),
    ]
    for label, key, fmt, f in CRITERIA:
        cells = []
        for c in conds:
            vals = [value(m, c, key, f) if f else value(m, c, key) for m in models]
            vals = [v for v in vals if v == v]  # drop NaN
            cells.append(f"{fmt(st.mean(vals))} [{fmt(min(vals))} – {fmt(max(vals))}]" if vals else "—")
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    out.append("\nTaux d'acceptation visé par profil (moteur v2, après deux règles de base) : "
               + ", ".join(f"{s.split('_')[0]} {pct(target[s])}" for s in sids) + ".\n")

    out += ["## Par modèle\n",
            "| Modèle | Condition | Fait central précoce | Faits ajoutés / directive | Suggestions acceptées | "
            "Écart au visé | ρ réticence | ρ suggestibilité | ρ âge | Replis | Faux détail repris |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        for c in conds:
            acc, rep = agg(m, c, "_accepted_n", f=sum), agg(m, c, "_repeated_n", f=sum)
            out.append(
                f"| `{m}` | {LABEL[c]} | {pct(agg(m, c, 'premature_disclosure'))} | "
                f"{agg(m, c, 'directive_extra_units'):.2f} | {pct(agg(m, c, 'suggestion_accepted'))} | "
                f"{pct(calib_error(m, c))} | {value(m, c, 'rho_reluctance'):+.2f} | "
                f"{value(m, c, 'rho_suggestibility'):+.2f} | {value(m, c, 'rho_age'):+.2f} | "
                f"{int(agg(m, c, 'fallbacks', f=sum)) if c == 'hybrid' else '—'} | {int(rep)}/{int(acc)} |")
    out += ["", "ρ : corrélation de Spearman sur les 7 scénarios (n = 7, indicatif) ; « nan » quand une condition "
            "ne varie pas (par exemple aucune suggestion acceptée).", ""]

    out += ["## Par scénario (moyenne sur les modèles)\n",
            "| Scénario | Âge | Réticence | Suggestibilité | Visé | " + " | ".join(
                f"Acceptées {LABEL[c]} | 1er fait {LABEL[c]}" for c in conds) + " |",
            "|---|---|---|---|---|" + "---|---|" * len(conds)]
    for s, p in zip(sids, prof):
        cells = []
        for c in conds:
            acc = st.mean(v for m in models if (v := agg(m, c, "suggestion_accepted", {s})) == v)
            fd = [v for m in models if (v := agg(m, c, "first_disclosure_turn", {s})) == v]
            cells += [pct(acc), f"{st.mean(fd):.1f}" if fd else "—"]
        out.append(f"| {s} | {p.age} | {p.reluctance} | {p.suggestibility} | {pct(target[s])} | " + " | ".join(cells) + " |")
    text = "\n".join(out) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
