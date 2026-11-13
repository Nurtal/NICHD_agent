"""Behavior engine: deterministic state machine deciding what the child says each turn.

The engine never produces text. It emits a Decision (speech act + allowed units),
which a Realizer turns into a child utterance. All randomness goes through one
seeded RNG, so a given (scenario, seed, classification sequence) always yields
the same decisions.
"""

from __future__ import annotations

import random
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from nichd_sim.classification import OUT_OF_SCENARIO, Classification, QuestionType
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import Centrality, InfoUnit, Scenario
from nichd_sim.text import mentions, normalize


class SpeechAct(StrEnum):
    ANSWER = "answer"
    DONT_KNOW = "dont_know"
    ACQUIESCE = "acquiesce"
    DENY = "deny"
    CONFABULATE = "confabulate"
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
    effective_type: QuestionType | None = None
    """Question type the rules were applied for (the inner type of a compound question)."""
    lucky_suggestion: bool = False
    """A suggestive/closed question whose proposition happened to be true: still a technique fault."""
    new_contamination: str | None = None
    """Id of the contaminated unit created by this turn, if any."""


class ContaminatedUnit(BaseModel):
    id: str
    value: str
    target: str | None
    """Scenario unit the false detail is about, or None/out_of_scenario."""
    source_turn: int
    source_type: QuestionType
    integrated: bool
    """Durably integrated: may reappear spontaneously later."""
    times_said: int = 1


class EngineState(BaseModel):
    reluctance: float
    verbosity: float
    acquiescence: float
    revealed: list[str] = []
    """True unit ids said by the child, in order of first mention."""
    contaminated: list[ContaminatedUnit] = []
    last_unit: str | None = None
    turn: int = 0


def proposition_matches(unit: InfoUnit, proposition: str) -> bool:
    """Lexical consistency check: does the proposition mention the unit's anchors?"""
    norm = normalize(proposition)
    return any(mentions(norm, a) for a in unit.anchors)


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
        self.state.turn += 1
        effective = c.type
        if c.type == QuestionType.COMPOUND:
            effective = c.inner_type or QuestionType.DIRECTIVE
        handler = {
            QuestionType.INVITATION: self._invitation,
            QuestionType.CUED_INVITATION: self._cued_invitation,
            QuestionType.DIRECTIVE: self._directive,
            QuestionType.OPTION_POSING: self._option_posing,
            QuestionType.SUGGESTIVE: self._suggestive,
            QuestionType.FACILITATOR: self._facilitator,
            QuestionType.GROUND_RULE: self._acknowledge,
            QuestionType.SUPPORT: self._acknowledge,
            QuestionType.OTHER: self._confusion,
        }[effective]
        decision = handler(c, effective).model_copy(update={"effective_type": effective})
        self._commit(decision)
        return decision

    def record_confabulation(self, unit_id: str, text: str) -> None:
        """Store what the child actually invented (known only after realization)."""
        for cu in self.state.contaminated:
            if cu.id == unit_id:
                cu.value = text

    # -- probabilities ------------------------------------------------------

    def _suggestibility_factor(self) -> float:
        lo, hi = self.params["suggestibility_multiplier_range"]
        return lo + (hi - lo) * self.state.acquiescence

    def _p(self, name: str, modulated: bool = False) -> float:
        p = self.params[name] * (self._suggestibility_factor() if modulated else 1.0)
        return min(1.0, max(0.0, p))

    def _draw(self, p: float) -> bool:
        return self.rng.random() < p

    # -- open questions -----------------------------------------------------

    def _invitation_size(self) -> int:
        base = self.params["units_per_invitation"]
        lo, hi = self.params["verbosity_multiplier_range"]
        return max(1, round(base * (lo + (hi - lo) * self.state.verbosity)))

    def _unrevealed(self, pool: list[InfoUnit]) -> list[InfoUnit]:
        return [u for u in pool if u.id not in self.state.revealed]

    def _narrate(self, pool: list[InfoUnit], n: int, reason: str, recall_contamination: bool = False) -> Decision:
        """Pick up to n unrevealed units (central first, chronological order),
        possibly with one integrated false detail resurfacing."""
        fresh = self._unrevealed(pool)
        central = [u for u in fresh if u.centrality == Centrality.CENTRAL]
        peripheral = [u for u in fresh if u.centrality == Centrality.PERIPHERAL]
        units = [self._allowed(u) for u in (central + peripheral)[:n]]
        if recall_contamination:
            resurfacing = self._resurfacing_contamination()
            if resurfacing is not None:
                units.append(resurfacing)
                reason += " + faux détail intégré"
        if not units:
            return Decision(speech_act=SpeechAct.DONT_KNOW, reason=f"{reason} : plus rien à raconter")
        return Decision(speech_act=SpeechAct.ANSWER, allowed_units=units, reason=f"{reason} : {len(units)} unité(s)")

    def _resurfacing_contamination(self) -> AllowedUnit | None:
        integrated = [cu for cu in self.state.contaminated if cu.integrated]
        if not integrated or not self._draw(self.params["p_contamination_recall"]):
            return None
        cu = min(integrated, key=lambda x: (x.times_said, x.source_turn))
        cu.times_said += 1
        return AllowedUnit(id=cu.id, value=cu.value, contaminated=True, new=False)

    def _invitation(self, c: Classification, t: QuestionType) -> Decision:
        fresh = self._unrevealed(self._order)
        central_left = [u for u in fresh if u.centrality == Centrality.CENTRAL]
        return self._narrate(central_left or fresh, self._invitation_size(), "invitation", recall_contamination=True)

    def _cued_invitation(self, c: Classification, t: QuestionType) -> Decision:
        segment = self.scenario.segment_of(c.target) if c.target else None
        if segment is None:
            return self._invitation(c, t)
        pool = [u for s, u in self.scenario.all_units() if s == segment]
        if not self._unrevealed(pool):
            return self._invitation(c, t)
        return self._narrate(pool, self._invitation_size(), f"invitation indicée (segment {segment})", recall_contamination=True)

    def _facilitator(self, c: Classification, t: QuestionType) -> Decision:
        segment = self.scenario.segment_of(self.state.last_unit) if self.state.last_unit else None
        if segment is not None:
            pool = [u for s, u in self.scenario.all_units() if s == segment]
            if self._unrevealed(pool):
                return self._narrate(pool, 1, "facilitateur (suite du segment)")
        return self._narrate(self._order, 1, "facilitateur")

    # -- focused questions --------------------------------------------------

    def _target_unit(self, c: Classification) -> InfoUnit | None:
        if not c.target or c.target == OUT_OF_SCENARIO:
            return None
        return self.scenario.unit(c.target)

    def _directive(self, c: Classification, t: QuestionType) -> Decision:
        unit = self._target_unit(c)
        if unit is not None:
            return Decision(speech_act=SpeechAct.ANSWER, allowed_units=[self._allowed(unit)], reason=f"question directive → {unit.id}")
        if self._draw(self._p("p_confabulation", modulated=True)):
            cu = self._contaminate("(réponse inventée)", c, t, integrated=False)
            return Decision(
                speech_act=SpeechAct.CONFABULATE,
                allowed_units=[AllowedUnit(id=cu.id, value=cu.value, contaminated=True)],
                new_contamination=cu.id,
                reason="question directive hors scénario → confabulation",
            )
        return Decision(speech_act=SpeechAct.DONT_KNOW, reason="question directive hors scénario")

    def _option_posing(self, c: Classification, t: QuestionType) -> Decision:
        unit = self._target_unit(c)
        if c.options:
            return self._forced_choice(c, t, unit)
        return self._yes_no(c, t, unit)

    def _forced_choice(self, c: Classification, t: QuestionType, unit: InfoUnit | None) -> Decision:
        options = c.options or []
        correct = next((o for o in options if unit is not None and proposition_matches(unit, o)), None)
        if correct is not None and self._draw(self.params["p_correct_option"]):
            return Decision(
                speech_act=SpeechAct.ANSWER,
                allowed_units=[self._allowed(unit)],
                lucky_suggestion=True,
                reason=f"question à choix → bonne option ({correct!r})",
            )
        wrong = [o for o in options if o != correct]
        if not wrong:
            return Decision(speech_act=SpeechAct.DONT_KNOW, reason="question à choix → je sais pas")
        if self._draw(self.params["p_recency"]):
            choice, why = wrong[-1], "biais de récence"
        elif correct is not None:
            choice, why = self.rng.choice(wrong), "mauvaise option"
        else:
            return Decision(speech_act=SpeechAct.DONT_KNOW, reason="question à choix sans bonne option → je sais pas")
        cu = self._contaminate(choice, c, t, integrated=self._draw(self._p("p_integration", modulated=True)))
        return Decision(
            speech_act=SpeechAct.ACQUIESCE,
            allowed_units=[AllowedUnit(id=cu.id, value=choice, contaminated=True)],
            new_contamination=cu.id,
            reason=f"question à choix → {why} ({choice!r})",
        )

    def _yes_no(self, c: Classification, t: QuestionType, unit: InfoUnit | None) -> Decision:
        prop = c.suggested_proposition
        if unit is not None and (prop is None or proposition_matches(unit, prop)):
            return Decision(
                speech_act=SpeechAct.ANSWER,
                allowed_units=[self._allowed(unit)],
                lucky_suggestion=True,
                reason=f"question oui/non vraie → {unit.id}",
            )
        if prop and self._draw(self._p("p_yes_bias", modulated=True)):
            cu = self._contaminate(prop, c, t, integrated=self._draw(self._p("p_integration", modulated=True)))
            return Decision(
                speech_act=SpeechAct.ACQUIESCE,
                allowed_units=[AllowedUnit(id=cu.id, value=prop, contaminated=True)],
                new_contamination=cu.id,
                reason="question oui/non fausse → biais d'acquiescement",
            )
        return Decision(speech_act=SpeechAct.DENY, reason="question oui/non fausse → non")

    def _suggestive(self, c: Classification, t: QuestionType) -> Decision:
        unit = self._target_unit(c)
        prop = c.suggested_proposition
        if unit is not None and (prop is None or proposition_matches(unit, prop)):
            return Decision(
                speech_act=SpeechAct.ACQUIESCE,
                allowed_units=[self._allowed(unit)],
                lucky_suggestion=True,
                reason=f"suggestion tombée juste → {unit.id}",
            )
        if prop and self._draw(self._p("p_acquiesce", modulated=True)):
            cu = self._contaminate(prop, c, t, integrated=self._draw(self._p("p_integration", modulated=True)))
            return Decision(
                speech_act=SpeechAct.ACQUIESCE,
                allowed_units=[AllowedUnit(id=cu.id, value=prop, contaminated=True)],
                new_contamination=cu.id,
                reason=f"suggestion fausse → acquiescement{' + intégration' if cu.integrated else ''}",
            )
        return Decision(speech_act=SpeechAct.DENY, reason="suggestion fausse → refus")

    # -- other --------------------------------------------------------------

    def _acknowledge(self, c: Classification, t: QuestionType) -> Decision:
        return Decision(speech_act=SpeechAct.ACKNOWLEDGE, reason=f"{t}")

    def _confusion(self, c: Classification, t: QuestionType) -> Decision:
        return Decision(speech_act=SpeechAct.CONFUSION, reason="énoncé hors protocole")

    # -- helpers ------------------------------------------------------------

    def _contaminate(self, value: str, c: Classification, t: QuestionType, integrated: bool) -> ContaminatedUnit:
        cu = ContaminatedUnit(
            id=f"c{len(self.state.contaminated) + 1}",
            value=value,
            target=c.target,
            source_turn=self.state.turn,
            source_type=c.type,
            integrated=integrated,
        )
        self.state.contaminated.append(cu)
        return cu

    def _allowed(self, unit: InfoUnit) -> AllowedUnit:
        return AllowedUnit(id=unit.id, value=unit.value, new=unit.id not in self.state.revealed)

    def _commit(self, decision: Decision) -> None:
        for au in decision.allowed_units:
            if not au.contaminated and au.id not in self.state.revealed:
                self.state.revealed.append(au.id)
        true_units = [au for au in decision.allowed_units if not au.contaminated]
        if true_units:
            self.state.last_unit = true_units[-1].id
