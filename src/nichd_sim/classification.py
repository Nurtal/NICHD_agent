"""Interviewer utterance classification (NICHD typology) and the classifier port."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from nichd_sim.scenario import Scenario

OUT_OF_SCENARIO = "out_of_scenario"


class QuestionType(StrEnum):
    INVITATION = "invitation"
    CUED_INVITATION = "cued_invitation"
    DIRECTIVE = "directive"
    OPTION_POSING = "option_posing"
    SUGGESTIVE = "suggestive"
    FACILITATOR = "facilitator"
    GROUND_RULE = "ground_rule"
    SUPPORT = "support"
    COMPOUND = "compound"
    OTHER = "other"


QUESTION_TYPES = {
    QuestionType.INVITATION,
    QuestionType.CUED_INVITATION,
    QuestionType.DIRECTIVE,
    QuestionType.OPTION_POSING,
    QuestionType.SUGGESTIVE,
}


class SegmentHint(StrEnum):
    BEFORE = "before"
    DURING = "during"
    AFTER = "after"


class GroundRuleKind(StrEnum):
    DONT_KNOW = "dont_know"
    DONT_UNDERSTAND = "dont_understand"
    CORRECT_ME = "correct_me"
    NOT_THERE = "not_there"
    TRUTH = "truth"
    PROMISE = "promise"
    PRACTICE = "practice"
    """A practice question on a rule (« si je te demande le nom de mon chien, tu dis quoi ? »)."""


class PracticeKind(StrEnum):
    EPISODIC = "episodic"
    GENERIC = "generic"


class Classification(BaseModel):
    """Output of the classifier for one interviewer utterance."""

    model_config = ConfigDict(frozen=True)

    type: QuestionType
    target: str | None = None
    """Targeted info unit id (or the cue's unit for a cued invitation), or OUT_OF_SCENARIO."""
    suggested_proposition: str | None = None
    options: list[str] | None = None
    """Options offered by an option-posing question, in the order they were stated."""
    inner_type: QuestionType | None = None
    """For a compound question: type of its most directive element (drives the engine)."""
    phase_hints: list[str] = []
    segment: SegmentHint | None = None
    """Part of the event the prompt asks about (« raconte-moi la fin »), skill 0.3.0."""
    knowledge_question: bool = False
    """« Est-ce que tu sais / te souviens… ? »: asks yes/no, implicitly asks for the information."""
    ground_rule_kind: GroundRuleKind | None = None
    """For a ground rule: which one (stated rules, the truth promise, a practice question)."""
    practice_kind: PracticeKind | None = None
    """For a narrative-practice invitation: about one past occasion (episodic) or habits (generic)."""
    causal: bool = False
    """Asks for a reason or a cause (« pourquoi… ? »): never answered by a bare yes or no."""
    meta: dict = {}
    """Classifier diagnostics (model, latency, errors). Logged, never used by the engine."""
    clean_text: str | None = None
    """Utterance as the child hears it, when the classifier input carried annotations."""


@dataclass
class ClassificationContext:
    """What the classifier may know when classifying an utterance."""

    scenario: Scenario
    revealed_unit_ids: list[str] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)
    """(speaker, text) pairs; speaker is 'interviewer' or 'child'."""


class Classifier(Protocol):
    def classify(self, utterance: str, context: ClassificationContext) -> Classification: ...
