"""Controlled lie/truth pairs: same session, same question about the same protected fact; only the
child's will to conceal differs (deception strength 1.0 vs 0.0). Lying is then the ONLY difference.
"""

from __future__ import annotations

from doubles import C, ask, make_session
from sim import scenarios

from nichd_sim.engine import Decision

QUESTIONS = {
    "directive": lambda u: C("directive", u.id),
    "option_posing": lambda u: C("option_posing", u.id, suggested_proposition=u.anchors[0]),
    "suggestive": lambda u: C("suggestive", u.id, suggested_proposition=u.anchors[0]),
}


def pairs(seeds=range(50), overrides: dict | None = None) -> list[tuple[str, Decision, Decision]]:
    """(question type, lie decision, truth decision) for every seed × protected fact × question type."""
    base = next(s for s in scenarios(deception_variants=False) if s.deception is not None)
    base = base.model_copy(update={"parameter_overrides": {**base.parameter_overrides, **(overrides or {})}})
    out = []
    for seed in seeds:
        for uid in base.deception.protected:
            unit = base.unit(uid)
            for qtype, make in QUESTIONS.items():
                decisions = []
                for strength in (1.0, 0.0):
                    sc = base.model_copy(update={"deception": base.deception.model_copy(update={"strength": strength})})
                    s, clf, _ = make_session(sc, seed=seed)
                    for i, c in enumerate([C("support"), C("invitation", phase_hints=["transition"]),
                                           C("invitation", phase_hints=["transition"]), C("invitation")]):
                        ask(s, clf, f"w{i}", c)
                    decisions.append(ask(s, clf, "q", make(unit)).decision)
                lie, truth = decisions
                if lie.lie is not None and truth.lie is None and uid not in [] and truth.allowed_units:
                    out.append((qtype, lie, truth))
    return out
