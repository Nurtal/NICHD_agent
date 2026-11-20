"""Behavioural fidelity of the child engine against the literature (docs/plans/adaptations-litterature.md).

    uv run python experiments/fidelity/run.py [--seeds 100] [--out docs/evaluations/fidelite.md]

Each probe drives the BehaviorEngine directly with scripted, gold-labelled prompts (manual-classifier
syntax, no LLM, no realization) over many seeds, and measures one regularity documented in
docs/research/confrontation-modele-litterature.md. The report says, per probe, the target from the
literature and whether the current engine meets it. Lot 0 records the baseline, before any adaptation.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "ablation"))

from protocol import PLANS  # noqa: E402

from nichd_sim.classification import Classification, ClassificationContext, QuestionType  # noqa: E402
from nichd_sim.classifiers.manual import ManualClassifier  # noqa: E402
from nichd_sim.demeanor import CueFamily  # noqa: E402
from nichd_sim.engine import BehaviorEngine, Decision, SpeechAct  # noqa: E402
from nichd_sim.parameters import Parameters  # noqa: E402
from nichd_sim.scenario import Scenario, load_scenario  # noqa: E402

SCENARIOS = ROOT / "scenarios"
_MANUAL = ManualClassifier()
_WAIT = Classification(type=QuestionType.FACILITATOR, clean_text="")


class Child:
    """One simulated child: the engine plus the manual tags of the scripted prompts."""

    def __init__(self, scenario: Scenario, seed: int, **profile):
        if profile:
            scenario = scenario.model_copy(update={"child_profile": scenario.child_profile.model_copy(update=profile)})
        self.scenario = scenario
        params = Parameters.load(scenario.child_profile.age_band, scenario.parameter_overrides)
        self.engine = BehaviorEngine(scenario, params, seed)
        self.decisions: list[Decision] = []

    def ask(self, line: str) -> Decision:
        c = _MANUAL.classify(line, ClassificationContext(scenario=self.scenario))
        heard = c.clean_text or line.split("]", 1)[-1].strip()
        d = self.engine.decide(c, utterance=heard)
        self.decisions.append(d)
        return d

    def wait(self) -> Decision:
        """The interviewer says nothing (wait turn)."""
        d = self.engine.decide(_WAIT, wait=True)
        self.decisions.append(d)
        return d

    @property
    def state(self):
        return self.engine.state


def true_units(d: Decision) -> int:
    return sum(1 for u in d.allowed_units if not u.contaminated and not u.lie)


def accepted_false(d: Decision) -> bool:
    """The child took up a false proposition (acquiescence or a contaminated detail)."""
    return d.speech_act in (SpeechAct.ACQUIESCE, SpeechAct.CONFABULATE) or any(u.contaminated for u in d.allowed_units)


def rate(xs: list[bool]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def disclose(child: Child, max_turns: int = 6) -> bool:
    for _ in range(max_turns):
        child.ask("[inv] Raconte-moi tout ce qui s'est passé.")
        if child.state.disclosed:
            return True
    return False


# -- probes -------------------------------------------------------------------------


@dataclass
class Result:
    piste: str
    mesure: str
    valeurs: str
    cible: str
    atteinte: bool | None  # None: not measurable before a later lot


def probe_repetition(seeds: range) -> Result:
    """A2 — Krähenbühl et al. (2009): repeated unanswerable questions → more invention."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    q = PLANS[sc.id].out_of_scenario[0]
    by_rank: list[list[bool]] = [[] for _ in range(4)]
    changed: list[bool] = []
    for seed in seeds:
        child = Child(sc, seed)
        if not disclose(child):
            continue
        acts = [child.ask(f"[dir:hors] {q}") for _ in range(4)]
        for k, d in enumerate(acts):
            by_rank[k].append(d.speech_act == SpeechAct.CONFABULATE)
        changed += [a.speech_act != b.speech_act for a, b in zip(acts, acts[1:])]
    rates = [rate(r) for r in by_rank]
    return Result(
        "A2", "invention à la 1ʳᵉ, 2ᵉ, 3ᵉ, 4ᵉ question hors scénario identique ; réponses qui changent",
        " / ".join(f"{r:.0%}" for r in rates) + f" ; {rate(changed):.0%} de changements",
        "invention croissante ; > 25 % de réponses qui changent",
        rates[-1] > rates[0] + 0.05 and rate(changed) > 0.25,
    )


def probe_dont_know_reaction(seeds: range) -> Result:
    """A1 — Bücken et al. (2026): after a rejected « je sais pas » most children answer anyway (76–81 %,
    at the risk of complying), and an accepted one leaves the child more forthcoming."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    q = PLANS[sc.id].out_of_scenario[1]
    units: dict[str, list[int]] = {"accept": [], "reject": []}
    answered_rejection: list[bool] = []
    for branch in units:
        for seed in seeds:
            child = Child(sc, seed)
            if not disclose(child, 1):
                continue
            if child.ask(f"[dir:hors] {q}").speech_act != SpeechAct.DONT_KNOW:
                continue
            if branch == "accept":
                child.ask("[soutien] D'accord, c'est bien de me dire quand tu ne sais pas.")
            else:
                answered_rejection.append(child.ask(f"[dir:hors] {q}").speech_act != SpeechAct.DONT_KNOW)
            units[branch].append(true_units(child.ask("[inv] Raconte-moi encore ce qui s'est passé.")))
    mean = {b: statistics.mean(v) if v else 0.0 for b, v in units.items()}
    answered = rate(answered_rejection)
    return Result(
        "A1", "unités vraies à l'invitation suivante (accepté / rejeté) ; réponse donnée au rejet",
        f"{mean['accept']:.2f} / {mean['reject']:.2f} unités ; {answered:.0%} répondent au rejet"
        f" (n = {len(units['accept'])} / {len(units['reject'])})",
        "accepté > rejeté ; une majorité répond au rejet (76–81 %, souvent par complaisance)",
        mean["accept"] > mean["reject"] and answered > 0.5,
    )


def probe_pressure(seeds: range) -> Result:
    """A3 — Hershkowitz et al. (2006): with a reluctant child, invitations + support beat suggestive pressure."""
    sc = load_scenario(SCENARIOS / "s02_violences_maison.yaml")
    uid, question = PLANS[sc.id].directives[0]
    value = {u.id: u for _, u in sc.target_units()}[uid].value
    paths = {  # the suggestion is true: pressure can force the disclosure (a lucky suggestion)
        "invitations": ["[soutien] Je suis là pour t'écouter.", "[soutien] Tu peux prendre ton temps."]
        + ["[inv] Raconte-moi ce qui s'est passé à la maison."] * 6,
        "suggestives": [f"[sug:{uid}={value}] C'est vrai que {value}, hein ?"] * 8,
    }
    when: dict[str, list[int]] = {}
    for name, lines in paths.items():
        when[name] = []
        for seed in seeds:
            child = Child(sc, seed)
            for k, line in enumerate(lines, 1):
                child.ask(line)
                if child.state.disclosed:
                    when[name].append(k)
                    break
            else:
                when[name].append(len(lines) + 1)  # not disclosed: counted after the last turn
    mean = {n: statistics.mean(v) for n, v in when.items()}
    return Result(
        "A3", "enfant réticent (s02) : tour moyen du dévoilement, 2 soutiens puis invitations / suggestives vraies",
        f"{mean['invitations']:.1f} / {mean['suggestives']:.1f}",
        "la pression ne doit pas être le chemin le plus rapide (invitations ≤ suggestives)",
        mean["invitations"] <= mean["suggestives"],
    )


def probe_support_acquiescence(seeds: range) -> Result:
    """A6 — Saywitz et al. (2019): support lowers acquiescence to false suggestions."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    s1 = PLANS[sc.id].false_suggestions[0][0]
    res = {}
    for supports in (0, 2):
        hits = []
        for seed in seeds:
            child = Child(sc, seed)
            if not disclose(child, 1):
                continue
            for _ in range(supports):
                child.ask("[soutien] Tu fais de ton mieux, c'est très bien.")
            hits.append(accepted_false(child.ask(f"[sug:hors={s1}] {s1}")))
        res[supports] = rate(hits)
    return Result(
        "A6", "acquiescement à une suggestion fausse après 0 / 2 énoncés de soutien",
        f"{res[0]:.0%} / {res[2]:.0%}", "baisse avec le soutien", res[2] < res[0] - 0.02,
    )


def probe_lie_forms(seeds: range) -> Result:
    """A9 — Talwar et al. (2004): leaving the fact out is far more frequent than denying it."""
    sc = load_scenario(SCENARIOS / "s08_violences_maison_secret.yaml")
    unit = {u.id: u for _, u in sc.target_units()}
    lines = ["[soutien] Je suis là pour t'écouter."] + ["[inv] Raconte-moi tout ce qui s'est passé."] * 3
    for uid in ("d_karim", "d_bras", "d_tape"):
        lines.append(f"[choix:{uid}={unit[uid].value}] Est-ce que {unit[uid].value} ?")
    kinds: Counter = Counter()
    for seed in seeds:
        child = Child(sc, seed)
        for line in lines:
            child.ask(line)
        kinds.update(lr.kind.value for lr in child.state.lies)
    total = sum(kinds.values()) or 1
    share = {k: kinds[k] / total for k in ("omission", "false_deny", "feigned_ignorance", "cover_story", "minimization")}
    return Result(
        "A9", "s08, 3 récits puis 3 oui/non vrais : omission / déni / feinte d'ignorance / couverture / minimisation",
        " / ".join(f"{v:.0%}" for v in share.values()) + f" (n = {sum(kinds.values())})",
        "omissions > dénis (Talwar et al., 2004)", share["omission"] > share["false_deny"],
    )


def probe_promise(seeds: range) -> Result:
    """A8 — Talwar et al. (2004): the promise to tell the truth cuts lying about a parent's fault."""
    sc = load_scenario(SCENARIOS / "s08_violences_maison_secret.yaml")
    protected = set(sc.deception.protected)

    def told(promise: bool) -> float:
        counts = []
        for seed in seeds:
            child = Child(sc, seed, reluctance=0.0)
            if promise:
                child.ask("[regle+promesse] Tu me promets de dire seulement la vérité ?")
            for _ in range(4):
                child.ask("[inv] Raconte-moi tout ce qui s'est passé.")
            counts.append(len(protected & set(child.state.revealed)))
        return statistics.mean(counts)
    without, with_ = told(False), told(True)
    return Result(
        "A8", f"s08 : faits protégés révélés après 4 récits, sans / avec promesse (sur {len(protected)})",
        f"{without:.2f} / {with_:.2f}", "plus de faits révélés avec la promesse", with_ > without,
    )


def probe_leak(seeds: range) -> Result:
    """A9 — Talwar & Lee (2002), Talwar et al. (2007): younger liars give themselves away at follow-ups."""
    sc = load_scenario(SCENARIOS / "s08_violences_maison_secret.yaml")
    rates = []
    for age in (5, 8, 11):
        leaks = []
        for seed in seeds:
            child = Child(sc, seed, reluctance=0.0, age=age)
            child.engine.state.concealment = 1.0
            if child.ask("[dir:d_karim] Qui était là ?").lie is None:
                continue
            leaks.append(child.ask("[dir:d_karim] C'était qui, le monsieur ?").speech_act == SpeechAct.LEAK)
        rates.append(rate(leaks))
    return Result(
        "A9", "s08 : la vérité échappe à la question de suite sur un mensonge, à 5 / 8 / 11 ans",
        " / ".join(f"{r:.0%}" for r in rates), "décroissant avec l'âge", rates[0] > rates[1] > rates[2],
    )


def probe_wait(seeds: range) -> Result:
    """A12 — Rezmer et al. (2020): a long wait after the answer often brings more information."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    gains, waited = [], []
    for seed in seeds:
        child = Child(sc, seed)
        for _ in range(2):
            child.ask("[inv] Raconte-moi tout ce qui s'est passé.")
        before = len(child.state.revealed)
        child.wait()
        waited.append(len(child.state.revealed) - before)
    m = statistics.mean(waited)
    return Result("A12", "s01 : unités vraies ajoutées par un tour d'attente après deux récits (même seed)",
                  f"+{m:.2f} ; {rate([w > 0 for w in waited]):.0%} des enfants complètent", "> 0, souvent", m > 0.3)


def probe_arousal_before_disclosure(seeds: range) -> Result:
    """A11 — Karni-Visel et al. (2023): non-verbal signs precede the verbal disclosure."""
    sc = load_scenario(SCENARIOS / "s02_violences_maison.yaml")
    deltas = []
    for seed in seeds:
        child = Child(sc, seed)
        trace = []
        for _ in range(8):
            child.ask("[inv] Raconte-moi ce qui s'est passé à la maison.")
            trace.append(child.state.arousal)
            if child.state.disclosed:
                break
        if child.state.disclosed and len(trace) >= 3:
            deltas.append(trace[-2] - trace[-3])  # the turn just before disclosure
    m = statistics.mean(deltas) if deltas else 0.0
    return Result("A11", "s02 : variation d'activation au tour qui précède le dévoilement", f"{m:+.3f}",
                  "hausse avant le dévoilement", m > 0.01)


def probe_support_expressivity(seeds: range) -> Result:
    """A10 — Karni-Visel et al. (2023): support goes with more non-verbal emotional expression."""
    sc = load_scenario(SCENARIOS / "s02_violences_maison.yaml")
    emotion = {CueFamily.TEARS, CueFamily.TREMOR, CueFamily.TENSION}
    res = {}
    for supports in (0, 3):
        counts = []
        for seed in seeds:
            child = Child(sc, seed)
            for _ in range(supports):
                child.ask("[soutien] Je suis là pour t'écouter.")
            for _ in range(4):
                d = child.ask("[inv] Raconte-moi ce qui s'est passé à la maison.")
            counts.append(sum(1 for cue in (d.demeanor.cues if d.demeanor else []) if cue.cue.family in emotion))
        res[supports] = statistics.mean(counts)
    return Result("A10", "s02 : signes d'émotion au 4ᵉ récit, sans / avec 3 énoncés de soutien",
                  f"{res[0]:.2f} / {res[3]:.2f}", "plus de signes avec le soutien", res[3] > res[0])


def probe_segment(seeds: range) -> Result:
    """A4 — NICHD protocol (Lamb et al., 2007): « raconte-moi la fin » asks for the end."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    after = {u.id for seg, u in sc.target_units() if str(seg) == "after"}
    ok = []
    for seed in seeds:
        child = Child(sc, seed)
        if not disclose(child, 1):
            continue
        d = child.ask("[inv+fin] Raconte-moi la fin.")
        told = {u.id for u in d.allowed_units if not u.contaminated and not u.lie}
        ok.append(bool(told) and told <= after)
    return Result("A4", "« Raconte-moi la fin » : réponses qui ne livrent que le segment final", f"{rate(ok):.0%}",
                  "100 %", rate(ok) == 1.0)


def probe_knowledge_question(seeds: range) -> Result:
    """A5 — Evans et al. (2014, 2017): « tu te souviens… ? » often gets a bare « oui », less with age."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    res = {}
    for age in (5, 8, 11):
        hits = []
        for seed in seeds:
            child = Child(sc, seed, age=age)
            if not disclose(child, 1):
                continue
            hits.append(child.ask("[choix+sais:d_pousse] Tu te souviens qui a poussé ?").speech_act == SpeechAct.AFFIRM)
        res[age] = rate(hits)
    return Result("A5", "« oui » sans détail à « Tu te souviens qui… ? », à 5 / 8 / 11 ans",
                  " / ".join(f"{v:.0%}" for v in res.values()),
                  "décroissant avec l'âge ; de l'ordre de 15 à 45 % chez les plus jeunes",
                  res[5] > res[8] > res[11] and 0.15 <= res[5] <= 0.5)


def probe_ground_rule_practice(seeds: range) -> Result:
    """A7 — Earhart et al. (2014); Brubacher et al. (2015): stating a rule does little, practising it more."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    q = PLANS[sc.id].out_of_scenario[0]
    res = {}
    for name, rule in (("aucune", None), ("énoncée", "[regle+jsp@regles] Si tu ne sais pas, dis « je ne sais pas »."),
                       ("entraînée", "[regle+entrainement@regles] Si je te demande le nom de mon chien, tu dis quoi ?")):
        hits = []
        for seed in seeds:
            child = Child(sc, seed, age=8)
            for _ in range(3 if rule else 0):
                child.ask(rule)
            if not disclose(child, 1):
                continue
            hits.append(child.ask(f"[dir:hors] {q}").speech_act == SpeechAct.CONFABULATE)
        res[name] = rate(hits)
    return Result("A7", "invention à une question hors scénario (8 ans) : sans règle / 3 règles énoncées / 3 entraînées",
                  " / ".join(f"{v:.0%}" for v in res.values()),
                  "énoncée : effet faible ; entraînée : effet net",
                  res["aucune"] - res["énoncée"] < res["aucune"] - res["entraînée"])


def probe_causal(seeds: range) -> Result:
    """A15 — a « why » question is open: never a bare « oui » or « non »."""
    sc = load_scenario(SCENARIOS / "s01_bagarre_parc.yaml")
    bad = []
    for seed in seeds:
        child = Child(sc, seed)
        if not disclose(child, 1):
            continue
        d = child.ask("[choix+pourquoi:hors=il l'a poussé] Pourquoi il l'a poussé ?")
        bad.append(d.speech_act in (SpeechAct.DENY, SpeechAct.ACQUIESCE, SpeechAct.AFFIRM))
    return Result("A15", "« Pourquoi… ? » codé fermé : réponses oui/non", f"{rate(bad):.0%}", "0 %", rate(bad) == 0)


PROBES: list[Callable[[range], Result]] = [
    probe_dont_know_reaction, probe_repetition, probe_pressure, probe_support_acquiescence,
    probe_segment, probe_knowledge_question, probe_ground_rule_practice, probe_causal,
    probe_lie_forms, probe_promise, probe_leak, probe_wait, probe_support_expressivity, probe_arousal_before_disclosure,
]
LATER = [
]


def report(results: list[Result], seeds: int) -> str:
    mark = {True: "oui", False: "**non**", None: "—"}
    lines = [
        "# Fidélité comportementale du moteur",
        "",
        "*Produit par `experiments/fidelity/run.py`. Chaque sonde pilote le moteur avec des énoncés étiquetés "
        f"(classifieur manuel, sans LLM) sur {seeds} seeds. Les cibles viennent de la "
        "[confrontation à la littérature](../research/confrontation-modele-litterature.md) ; le plan est dans "
        "[docs/plans/adaptations-litterature.md](../plans/adaptations-litterature.md).*",
        "",
        "| Piste | Mesure | Valeur | Cible | Atteinte |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {r.piste} | {r.mesure} | {r.valeurs} | {r.cible} | {mark[r.atteinte]} |" for r in results]
    if LATER:
        lines += ["", "**Pas encore mesurables** (champs ou mécanismes à venir) :", ""]
        lines += [f"- {p} : {m} ({when})." for p, m, when in LATER]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--out", type=Path, help="écrire le rapport Markdown (sinon : sortie standard)")
    args = ap.parse_args()
    seeds = range(args.seeds)
    text = report([probe(seeds) for probe in PROBES], args.seeds)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
