"""Simulated interviews for the voice evaluation: varied interviewers, no LLM.

A "random interviewer" follows the protocol's shape (rapport → ground rules → practice →
transition → substantive → closure) but draws its substantive questions from a style mix,
from a very open interviewer to a very closed one, with true and false propositions. Every
child reply comes with its Decision (delivery, lie, units) — the ground truth of the evaluation.

Run from the repository root with the project env (it imports tests/doubles.py).
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from doubles import C, ask, make_session

from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.engine import Decision
from nichd_sim.scenario import Scenario, load_scenario
from nichd_sim.session import TurnResult

STYLES = {
    # weights: invitation, cued, facilitator, directive, option, suggestive, support
    "ouvert": (5, 3, 2, 1, 0.3, 0.1, 1),
    "mixte": (3, 2, 1, 3, 1.5, 0.7, 0.7),
    "fermé": (1, 0.5, 0.5, 4, 3, 2, 0.3),
}
KINDS = ["invitation", "cued_invitation", "facilitator", "directive", "option_posing", "suggestive", "support"]


@dataclass
class Reply:
    scenario: str
    seed: int
    style: str
    age_band: str
    turn: int
    question_type: str
    result: TurnResult

    @property
    def decision(self) -> Decision:
        return self.result.decision


def scenarios(deception_variants: bool = True) -> list[Scenario]:
    """The 8 scenario sheets; s08 also at low and high concealment, to get enough lies."""
    out = [load_scenario(p) for p in sorted((ROOT / "scenarios").glob("s0*.yaml"))]
    if deception_variants:
        s08 = next(s for s in out if s.deception is not None)
        for strength in (0.4, 0.95):
            out.append(s08.model_copy(update={
                "id": f"{s08.id}@{strength}",
                "deception": s08.deception.model_copy(update={"strength": strength}),
            }))
    return out


def _question(rng: random.Random, sc: Scenario, style: str, revealed: list[str]):
    kind = rng.choices(KINDS, weights=STYLES[style])[0]
    units = [u for _, u in sc.target_units()]
    unit = rng.choice(units)
    if kind == "cued_invitation":
        return C(kind, rng.choice(revealed) if revealed else unit.id)
    if kind == "directive":
        return C(kind, unit.id if rng.random() < 0.85 else OUT_OF_SCENARIO)
    if kind in ("option_posing", "suggestive"):
        true = rng.random() < 0.5
        prop = unit.anchors[0] if true else rng.choice(["un couteau", "la nuit", "à l'école", "son oncle", "en voiture"])
        if kind == "option_posing" and rng.random() < 0.5:
            opts = [prop, rng.choice(["le matin", "dans la rue", "un monsieur"])]
            rng.shuffle(opts)
            return C(kind, unit.id, options=opts)
        return C(kind, unit.id, suggested_proposition=prop)
    return C(kind)


def interview(sc: Scenario, seed: int, style: str, n_substantive: int = 14) -> list[Reply]:
    rng = random.Random(f"{sc.id}:{seed}:{style}")
    s, clf, _ = make_session(sc, seed=seed)
    script = [C("support"), C("invitation", phase_hints=["rapport"]), C("ground_rule"), C("ground_rule"),
              C("invitation", phase_hints=["narrative_practice"]), C("facilitator")]
    script += [C("invitation", phase_hints=["transition"])] * 3
    replies = []
    for i in range(len(script) + n_substantive + 1):
        if i < len(script):
            c = script[i]
        elif i < len(script) + n_substantive:
            c = _question(rng, sc, style, s.state.revealed)
        else:
            c = C("invitation", phase_hints=["closure"])
        r = ask(s, clf, f"u{i}", c)
        replies.append(Reply(sc.id, seed, style, str(sc.child_profile.age_band), i + 1,
                             str(r.decision.effective_type or c.type), r))
    return replies


def corpus(seeds: range = range(5), styles=tuple(STYLES), deception_variants: bool = True) -> list[Reply]:
    return [r for sc in scenarios(deception_variants) for seed in seeds for style in styles
            for r in interview(sc, seed, style)]
