"""Phase tracker: infers the current NICHD interview phase and detects deviations.

Phases only move forward. The classifier's `phase_hints` drive the progression;
without hints (manual classification) the tracker infers what it can: ground
rules from `ground_rule` utterances, and the substantive phase from the child's
first disclosure of the target event.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from nichd_sim.classification import Classification, QuestionType
from nichd_sim.scenario import Scenario


class Phase(StrEnum):
    RAPPORT = "rapport"
    GROUND_RULES = "ground_rules"
    NARRATIVE_PRACTICE = "narrative_practice"
    TRANSITION = "transition"
    SUBSTANTIVE = "substantive"
    CLOSURE = "closure"


ORDER = list(Phase)

# Minimum interviewer turns for a preparatory phase not to count as truncated
# (protocol norm, not a psychological parameter).
MIN_TURNS = {Phase.RAPPORT: 2, Phase.GROUND_RULES: 2, Phase.NARRATIVE_PRACTICE: 3}

FOCUSED = {QuestionType.DIRECTIVE, QuestionType.OPTION_POSING, QuestionType.SUGGESTIVE}


class ViolationKind(StrEnum):
    SKIPPED_PHASE = "skipped_phase"
    TRUNCATED_PHASE = "truncated_phase"
    PREMATURE_FOCUSED_QUESTION = "premature_focused_question"
    MISSING_CLOSURE = "missing_closure"
    FORCED_DISCLOSURE = "forced_disclosure"


VIOLATION_LABELS = {
    ViolationKind.SKIPPED_PHASE: "phase sautée",
    ViolationKind.TRUNCATED_PHASE: "phase tronquée",
    ViolationKind.PREMATURE_FOCUSED_QUESTION: "question fermée ou directive sur les faits avant la transition",
    ViolationKind.MISSING_CLOSURE: "clôture absente",
    ViolationKind.FORCED_DISCLOSURE: "dévoilement obtenu par une question focalisée (directive, fermée ou suggestive)",
}


class PhaseViolation(BaseModel):
    kind: ViolationKind
    phase: Phase
    turn: int | None
    """Interviewer turn where it was detected (None: detected at the end of the session)."""
    detail: str = ""


class PhaseTracker:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.phase = Phase.RAPPORT
        self.turns_in_phase: dict[Phase, int] = {p: 0 for p in Phase}
        self.visited: list[Phase] = [Phase.RAPPORT]
        self.violations: list[PhaseViolation] = []
        self.turn = 0

    # -- per turn -----------------------------------------------------------

    def observe(self, c: Classification) -> Phase:
        """Update the phase from the interviewer's utterance (before the child answers)."""
        self.turn += 1
        candidate = self._candidate(c)
        if candidate is not None and ORDER.index(candidate) > ORDER.index(self.phase):
            self._advance(candidate)
        self.turns_in_phase[self.phase] += 1
        self._check_premature(c)
        return self.phase

    def after_decision(self, revealed_target: bool) -> Phase:
        """The child's first disclosure of the target event opens the substantive phase."""
        if revealed_target and ORDER.index(self.phase) < ORDER.index(Phase.SUBSTANTIVE):
            self._advance(Phase.SUBSTANTIVE)
        return self.phase

    def flag(self, kind: ViolationKind, detail: str = "") -> None:
        self.violations.append(PhaseViolation(kind=kind, phase=self.phase, turn=self.turn, detail=detail))

    def finish(self) -> list[PhaseViolation]:
        if self.phase != Phase.CLOSURE:
            self.violations.append(
                PhaseViolation(kind=ViolationKind.MISSING_CLOSURE, phase=Phase.CLOSURE, turn=None,
                               detail="l'entretien se termine sans phase de clôture")
            )
        return self.violations

    # -- internals ----------------------------------------------------------

    def _candidate(self, c: Classification) -> Phase | None:
        for hint in c.phase_hints:
            try:
                return Phase(hint)
            except ValueError:
                continue
        if c.type == QuestionType.GROUND_RULE:
            return Phase.GROUND_RULES
        return None

    def _advance(self, new: Phase) -> None:
        old = self.phase
        if old in MIN_TURNS and 0 < self.turns_in_phase[old] < MIN_TURNS[old]:
            self.violations.append(
                PhaseViolation(kind=ViolationKind.TRUNCATED_PHASE, phase=old, turn=self.turn,
                               detail=f"{self.turns_in_phase[old]} tour(s), minimum {MIN_TURNS[old]}")
            )
        for skipped in ORDER[ORDER.index(old) + 1 : ORDER.index(new)]:
            self.violations.append(PhaseViolation(kind=ViolationKind.SKIPPED_PHASE, phase=skipped, turn=self.turn))
        self.phase = new
        self.visited.append(new)

    def _check_premature(self, c: Classification) -> None:
        qtype = c.inner_type if c.type == QuestionType.COMPOUND and c.inner_type else c.type
        if qtype not in FOCUSED:
            return
        if ORDER.index(self.phase) >= ORDER.index(Phase.TRANSITION):
            return
        if self.scenario.is_target_unit(c.target):
            self.violations.append(
                PhaseViolation(kind=ViolationKind.PREMATURE_FOCUSED_QUESTION, phase=self.phase, turn=self.turn,
                               detail=f"{qtype} sur {c.target}")
            )
