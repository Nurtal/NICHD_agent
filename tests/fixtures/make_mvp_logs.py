"""Generate the v0.1-mvp reference logs used by the non-regression test.

Run it against the *MVP* code (tag v0.1-mvp), e.g. from a worktree:

    git worktree add /tmp/mvp v0.1-mvp
    cd /tmp/mvp && uv run python <repo>/tests/fixtures/make_mvp_logs.py <repo>/tests/fixtures/mvp_logs

Scripted classifications + template realizer: no LLM, fully deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path

from nichd_sim.classification import OUT_OF_SCENARIO, Classification, QuestionType
from nichd_sim.realization import TemplateRealizer
from nichd_sim.scenario import load_scenario
from nichd_sim.session import Session


class _Scripted:
    def __init__(self, items):
        self.items = list(items)

    def classify(self, utterance, context):
        return self.items.pop(0)


def script(sc) -> list[Classification]:
    T = QuestionType
    units = [u for _, u in sc.target_units()]
    first, mid, last = units[0], units[len(units) // 2], units[-1]
    C = lambda t, target=None, **kw: Classification(type=t, target=target, **kw)
    return [
        C(T.SUPPORT),
        C(T.INVITATION, phase_hints=["rapport"]),
        C(T.GROUND_RULE),
        C(T.GROUND_RULE),
        C(T.INVITATION, phase_hints=["narrative_practice"]),
        C(T.FACILITATOR),
        C(T.INVITATION, phase_hints=["transition"]),
        C(T.INVITATION, phase_hints=["transition"]),
        C(T.INVITATION),
        C(T.FACILITATOR),
        C(T.CUED_INVITATION, first.id),
        C(T.DIRECTIVE, mid.id),
        C(T.DIRECTIVE, OUT_OF_SCENARIO),
        C(T.OPTION_POSING, last.id, options=["dans la rue", "à l'école"]),
        C(T.OPTION_POSING, OUT_OF_SCENARIO, suggested_proposition="il avait un chapeau"),
        C(T.SUGGESTIVE, mid.id, suggested_proposition="il avait un couteau"),
        C(T.SUGGESTIVE, first.id, suggested_proposition=first.anchors[0]),
        C(T.COMPOUND, mid.id, inner_type=T.OPTION_POSING, suggested_proposition="c'était la nuit"),
        C(T.OTHER),
        C(T.INVITATION),
        C(T.INVITATION),
        C(T.INVITATION, phase_hints=["closure"]),
    ]


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path("scenarios").glob("s0*.yaml")):
        sc = load_scenario(path)
        for seed in (0, 1, 2):
            items = script(sc)
            s = Session(sc, _Scripted(items), TemplateRealizer(), seed=seed)
            for i in range(len(items)):
                s.turn(f"énoncé {i + 1}")
            log = s.end()
            log.session_id = f"mvp_{sc.id}_{seed}"
            (out / f"{log.session_id}.json").write_text(log.model_dump_json(), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
