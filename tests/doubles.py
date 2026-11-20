"""Test doubles for the two LLM ports."""

from __future__ import annotations

from pathlib import Path

from nichd_sim.classification import Classification, ClassificationContext, QuestionType
from nichd_sim.engine import Decision
from nichd_sim.parameters import Parameters
from nichd_sim.realization import Realization, TemplateRealizer
from nichd_sim.scenario import ChildProfile, Scenario, load_scenario
from nichd_sim.session import Session

ROOT = Path(__file__).resolve().parent.parent
S01 = ROOT / "scenarios" / "s01_bagarre_parc.yaml"


class ScriptedClassifier:
    """Returns classifications keyed by utterance, so tests read like dialogues."""

    def __init__(self, script: dict[str, Classification] | None = None):
        self.script = dict(script or {})
        self.contexts: list[ClassificationContext] = []

    def classify(self, utterance: str, context: ClassificationContext) -> Classification:
        self.contexts.append(context)
        return self.script[utterance]


class RecordingRealizer:
    def __init__(self):
        self.calls: list[tuple[Decision, ChildProfile, list]] = []
        self._inner = TemplateRealizer()

    def realize(self, decision, profile, history, attempt=0) -> Realization:
        self.calls.append((decision, profile, history))
        return self._inner.realize(decision, profile, history)


def C(type: str, target: str | None = None, **kw) -> Classification:
    return Classification(type=QuestionType(type), target=target, **kw)


def neutral_params(scenario: Scenario) -> Parameters:
    """The scenario's parameters with the interaction dynamics switched off (see `make_session`)."""
    overrides = {**Parameters.neutral_overrides(), **scenario.parameter_overrides}
    return Parameters.load(scenario.child_profile.age_band, overrides)


def make_session(
    scenario: Scenario | None = None, seed: int = 0, dynamics: bool = False, **kw
) -> tuple[Session, ScriptedClassifier, RecordingRealizer]:
    """`dynamics=False` (default): the rules added by docs/plans/adaptations-litterature.md are
    switched off, so tests of the base mechanics stay exact; tests of those rules pass True."""
    scenario = scenario or load_scenario(S01)
    if not dynamics and "params" not in kw:
        kw["params"] = neutral_params(scenario)
    clf, real = ScriptedClassifier(), RecordingRealizer()
    return Session(scenario, clf, real, seed=seed, **kw), clf, real


def ask(session: Session, clf: ScriptedClassifier, utterance: str, classification: Classification):
    clf.script[utterance] = classification
    return session.turn(utterance)


def with_profile(scenario: Scenario, **profile) -> Scenario:
    return scenario.model_copy(update={"child_profile": scenario.child_profile.model_copy(update=profile)})
