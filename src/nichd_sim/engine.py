"""Behavior engine: deterministic state machine deciding what the child says each turn.

The engine never produces text. It emits a Decision (speech act + allowed units),
which a Realizer turns into a child utterance.
"""

from __future__ import annotations

import random
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from nichd_sim.classification import OUT_OF_SCENARIO, Classification, QuestionType
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import Centrality, InfoUnit, Scenario


class SpeechAct(StrEnum):
    ANSWER = "answer"
    DONT_KNOW = "dont_know"
    ACQUIESCE = "acquiesce"
    DENY = "deny"
    ACKNOWLEDGE = "acknowledge"
    CONFUSION = "confusion"
    SILENCE = "silence"


class AllowedUnit(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    value: str
    contaminated: bool = False
    new: bool = True
    """False when the unit was already said in an earlier turn."""


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    speech_act: SpeechAct
    allowed_units: list[AllowedUnit] = []
    reason: str = ""
    """Short, human-readable trace of the rule applied (for trainer mode and logs)."""


class EngineState(BaseModel):
    reluctance: float
    verbosity: float
    acquiescence: float
    revealed: list[str] = []
    """True unit ids said by the child, in order of first mention."""
    last_unit: str | None = None


class BehaviorEngine:
    def __init__(self, scenario: Scenario, params: Parameters, seed: int):
        self.scenario = scenario
        self.params = params
        self.rng = random.Random(seed)
        profile = scenario.child_profile
        self.state = EngineState(
            reluctance=profile.reluctance,
            verbosity=profile.verbal_skills,
            acquiescence=profile.suggestibility,
        )
        self._order: list[InfoUnit] = [u for _, u in scenario.all_units()]

    # -- public -------------------------------------------------------------

    def decide(self, c: Classification) -> Decision:
        handler = {
            QuestionType.INVITATION: self._invitation,
            QuestionType.CUED_INVITATION: self._cued_invitation,
            QuestionType.DIRECTIVE: self._directive,
            QuestionType.FACILITATOR: self._facilitator,
            QuestionType.GROUND_RULE: self._acknowledge,
            QuestionType.SUPPORT: self._acknowledge,
            QuestionType.OTHER: self._confusion,
            # Placeholders until the dedicated rules land (#5): treat as directive.
            QuestionType.OPTION_POSING: self._directive,
            QuestionType.SUGGESTIVE: self._directive,
            QuestionType.COMPOUND: self._directive,
        }[c.type]
        decision = handler(c)
        self._commit(decision)
        return decision

    # -- rules --------------------------------------------------------------

    def _invitation_size(self) -> int:
        base = self.params["units_per_invitation"]
        lo, hi = self.params["verbosity_multiplier_range"]
        return max(1, round(base * (lo + (hi - lo) * self.state.verbosity)))

    def _unrevealed(self, pool: list[InfoUnit]) -> list[InfoUnit]:
        return [u for u in pool if u.id not in self.state.revealed]

    def _narrate(self, pool: list[InfoUnit], n: int, reason: str) -> Decision:
        """Pick up to n unrevealed units: central first, chronological order."""
        fresh = self._unrevealed(pool)
        central = [u for u in fresh if u.centrality == Centrality.CENTRAL]
        peripheral = [u for u in fresh if u.centrality == Centrality.PERIPHERAL]
        chosen = (central + peripheral)[:n]
        if not chosen:
            return Decision(speech_act=SpeechAct.DONT_KNOW, reason=f"{reason} : plus rien à raconter")
        return Decision(
            speech_act=SpeechAct.ANSWER,
            allowed_units=[self._allowed(u) for u in chosen],
            reason=f"{reason} : {len(chosen)} unité(s)",
        )

    def _invitation(self, c: Classification) -> Decision:
        n = self._invitation_size()
        fresh = self._unrevealed(self._order)
        central_left = [u for u in fresh if u.centrality == Centrality.CENTRAL]
        pool = central_left or fresh
        return self._narrate(pool, n, "invitation")

    def _cued_invitation(self, c: Classification) -> Decision:
        segment = self.scenario.segment_of(c.target) if c.target else None
        if segment is None:
            return self._invitation(c)
        pool = [u for s, u in self.scenario.all_units() if s == segment]
        decision = self._narrate(pool, self._invitation_size(), f"invitation indicée (segment {segment})")
        if decision.speech_act == SpeechAct.DONT_KNOW:
            return self._invitation(c)
        return decision

    def _directive(self, c: Classification) -> Decision:
        unit = self.scenario.unit(c.target) if c.target and c.target != OUT_OF_SCENARIO else None
        if unit is None:
            return Decision(speech_act=SpeechAct.DONT_KNOW, reason="question directive hors scénario")
        return Decision(
            speech_act=SpeechAct.ANSWER,
            allowed_units=[self._allowed(unit)],
            reason=f"question directive → {unit.id}",
        )

    def _facilitator(self, c: Classification) -> Decision:
        segment = self.scenario.segment_of(self.state.last_unit) if self.state.last_unit else None
        if segment is not None:
            pool = [u for s, u in self.scenario.all_units() if s == segment]
            if self._unrevealed(pool):
                return self._narrate(pool, 1, "facilitateur (suite du segment)")
        return self._narrate(self._order, 1, "facilitateur")

    def _acknowledge(self, c: Classification) -> Decision:
        return Decision(speech_act=SpeechAct.ACKNOWLEDGE, reason=f"{c.type}")

    def _confusion(self, c: Classification) -> Decision:
        return Decision(speech_act=SpeechAct.CONFUSION, reason="énoncé hors protocole")

    # -- helpers ------------------------------------------------------------

    def _allowed(self, unit: InfoUnit) -> AllowedUnit:
        return AllowedUnit(id=unit.id, value=unit.value, new=unit.id not in self.state.revealed)

    def _commit(self, decision: Decision) -> None:
        for au in decision.allowed_units:
            if not au.contaminated and au.id not in self.state.revealed:
                self.state.revealed.append(au.id)
        if decision.allowed_units:
            self.state.last_unit = decision.allowed_units[-1].id
