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
from nichd_sim.delivery import Delivery, HesitationCause, make_delivery
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import Centrality, EventKind, InfoUnit, LieUnit, Scenario
from nichd_sim.text import mentions, normalize


class SpeechAct(StrEnum):
    ANSWER = "answer"
    DONT_KNOW = "dont_know"
    ACQUIESCE = "acquiesce"
    DENY = "deny"
    CONFABULATE = "confabulate"
    ACKNOWLEDGE = "acknowledge"
    RELUCTANT = "reluctant"
    """Not ready to talk about the event yet: vague, evasive, no detail."""
    SMALL_TALK = "small_talk"
    """Rapport chit-chat about the child's life, without any scenario fact."""
    CONFUSION = "confusion"
    SILENCE = "silence"
    RETRACT = "retract"
    """Takes back an earlier lie and tells the true fact (ADR 0002)."""


class LieKind(StrEnum):
    OMISSION = "omission"
    """A protected fact left out of a free narrative."""
    FALSE_DENY = "false_deny"
    """« Non » to a true yes/no or suggestive question about a protected fact."""
    FEIGNED_IGNORANCE = "feigned_ignorance"
    """« Je sais pas » to a directive question about a protected fact."""
    COVER_STORY = "cover_story"
    MINIMIZATION = "minimization"


class LieRecord(BaseModel):
    """A lie told by the child: keeps it consistent across turns and feeds the metrics."""

    id: str
    kind: LieKind
    protected: str
    """Protected (true) unit the lie is about."""
    lie_unit: str | None = None
    """Author-written lie content said (cover story, minimization), if any."""
    value: str
    """What the child said instead of the truth."""
    turn: int
    question_type: QuestionType
    """Type of the question that drew the lie (effective type)."""
    times: int = 1
    retracted_turn: int | None = None


class AllowedUnit(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    value: str
    contaminated: bool = False
    new: bool = True
    """False when the unit was already said in an earlier turn."""
    lie: bool = False
    """Author-written lie content (cover story, minimization), not a true unit."""


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
    disclosure: bool = False
    """This turn is the child's first disclosure of the target event."""
    forced_disclosure: bool = False
    """The disclosure was obtained by a focused (directive, closed or suggestive) prompt."""
    delivery: Delivery | None = None
    """How the child says it (ADR 0002). None in logs older than format 2."""
    lie: LieRecord | None = None
    """The lie told at this turn (other than omissions), if any."""
    withheld: list[str] = []
    """Protected units deliberately left out of this turn's narrative (omission)."""
    retraction: LieRecord | None = None
    """The lie taken back at this turn (speech act `retract`)."""


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
    disclosed: bool = False
    disclosure_pressure: float = 0.0
    ground_rules_given: int = 0
    practice_turns: int = 0
    concealment: float = 0.0
    """Probability of hiding or disguising a protected fact (0 when the scenario has no deception)."""
    lies: list[LieRecord] = []


def proposition_matches(unit: InfoUnit, proposition: str) -> bool:
    """Lexical consistency check: does the proposition mention the unit's anchors?"""
    norm = normalize(proposition)
    return any(mentions(norm, a) for a in unit.anchors)


_FOCUSED = {QuestionType.DIRECTIVE, QuestionType.OPTION_POSING, QuestionType.SUGGESTIVE}

_FROM_HINT = object()  # sentinel: derive the topic from the utterance's phase hint


class BehaviorEngine:
    def __init__(self, scenario: Scenario, params: Parameters, seed: int):
        self.scenario = scenario
        self.params = params
        self.rng = random.Random(seed)
        # Separate streams (ADR 0002): new features never shift the decisions of the MVP stream.
        self.delivery_rng = random.Random(f"{seed}:delivery")
        self.deception_rng = random.Random(f"{seed}:deception")
        protected = scenario.deception.protected if scenario.deception else []
        draws = sorted((self.deception_rng.random() for _ in protected), reverse=True)
        self._thresholds = dict(zip(protected, draws))
        """Per protected fact, drawn once: the fact stays hidden while concealment exceeds it.
        Facts come out one by one as support lowers concealment (pressure hides them again), in
        the authored order: `protected` lists them from least to most guarded."""
        self._hidden: dict[str, bool] = {}
        """Per-turn concealment draws, so that a unit is hidden or not consistently within a turn."""
        profile = scenario.child_profile
        self.state = EngineState(
            reluctance=profile.reluctance,
            verbosity=profile.verbal_skills,
            acquiescence=profile.suggestibility,
            concealment=scenario.deception.strength if scenario.deception else 0.0,
        )
        self._orders: dict[EventKind, list[InfoUnit]] = {
            EventKind.TARGET: [u for _, u in scenario.target_units()],
            EventKind.NEUTRAL: [u for _, u in scenario.neutral_units()],
        }

    # -- public -------------------------------------------------------------

    def decide(self, c: Classification) -> Decision:
        self.state.turn += 1
        self._hidden = {}
        self._withheld: list[str] = []
        effective = c.type
        if c.type == QuestionType.COMPOUND:
            effective = c.inner_type or QuestionType.DIRECTIVE
        self._apply_phase_effects(c, effective)
        was_disclosed = self.state.disclosed
        about_target = self._about_target(c, effective)
        if not was_disclosed and about_target:
            gate = self._disclosure_gate(effective)
            if gate is not None:
                decision = gate.model_copy(update={"effective_type": effective})
                self._commit(decision)
                return self._with_delivery(decision, c, about_target)
        retraction = self._maybe_retract(effective)
        if retraction is not None:
            decision = retraction.model_copy(update={"effective_type": effective})
            self._commit(decision)
            return self._with_delivery(decision, c, about_target)
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
        decision = self._record_deception(decision, effective)
        self._commit(decision)
        if not was_disclosed and self.state.disclosed:
            decision = decision.model_copy(
                update={"disclosure": True, "forced_disclosure": effective in _FOCUSED}
            )
        return self._with_delivery(decision, c, about_target)

    # -- phase effects & disclosure ------------------------------------------

    def _apply_phase_effects(self, c: Classification, t: QuestionType) -> None:
        st, p = self.state, self.params
        hint = c.phase_hints[0] if c.phase_hints else None
        if t == QuestionType.SUPPORT:
            st.reluctance = max(0.0, st.reluctance - p["support_reluctance_drop"])
        elif t == QuestionType.INVITATION and hint == "rapport":
            st.reluctance = max(0.0, st.reluctance - p["rapport_reluctance_drop"])
        elif t == QuestionType.GROUND_RULE and st.ground_rules_given < p["max_effective_ground_rules"]:
            st.ground_rules_given += 1
            st.acquiescence = max(0.0, st.acquiescence - p["ground_rule_acquiescence_drop"])
        if self.scenario.deception is not None:
            if t == QuestionType.SUPPORT:
                st.concealment -= p["support_concealment_drop"]
            elif t == QuestionType.INVITATION and hint == "rapport":
                st.concealment -= p["rapport_concealment_drop"]
            elif t in (QuestionType.SUGGESTIVE, QuestionType.OPTION_POSING) and self.scenario.is_protected(c.target):
                st.concealment += p["pressure_concealment_rise"]
            st.concealment = round(min(1.0, max(0.0, st.concealment)), 6)
        if (
            t in (QuestionType.INVITATION, QuestionType.CUED_INVITATION)
            and hint == "narrative_practice"
            and st.practice_turns < p["max_effective_practice_turns"]
        ):
            st.practice_turns += 1
            st.verbosity = min(1.0, st.verbosity + p["narrative_practice_verbosity_boost"])

    def _about_target(self, c: Classification, t: QuestionType) -> bool:
        """Does this prompt push the child to talk about the target event?"""
        if t in (QuestionType.SUPPORT, QuestionType.GROUND_RULE, QuestionType.OTHER):
            return False
        if c.target and c.target != OUT_OF_SCENARIO:
            return self.scenario.is_target_unit(c.target)
        if t == QuestionType.FACILITATOR and self.state.last_unit:
            return self.scenario.is_target_unit(self.state.last_unit)
        return self._topic(c) == EventKind.TARGET

    def _disclosure_gate(self, t: QuestionType) -> Decision | None:
        """Accumulate pressure; None means the child discloses now."""
        st, p = self.state, self.params
        st.disclosure_pressure += p["disclosure_pressure"].get(str(t), 1.0)
        if st.reluctance >= p["no_disclosure_reluctance"]:
            return Decision(speech_act=SpeechAct.RELUCTANT, reason="trop réticent pour dévoiler")
        threshold = st.reluctance * p["disclosure_threshold_scale"]
        if st.disclosure_pressure >= threshold:
            return None
        return Decision(
            speech_act=SpeechAct.RELUCTANT,
            reason=f"pas encore prêt à dévoiler (pression {st.disclosure_pressure:.1f} / seuil {threshold:.1f})",
        )

    def unsay(self, unit_ids: list[str]) -> None:
        """The child was interrupted before saying these units: they are not revealed after all,
        and may be told later. (Lies and contaminations told in the same reply are kept.)"""
        st = self.state
        st.revealed = [u for u in st.revealed if u not in unit_ids]
        st.disclosed = any(self.scenario.is_target_unit(u) for u in st.revealed)
        st.last_unit = st.revealed[-1] if st.revealed else None

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
        return max(1, int(base * (lo + (hi - lo) * self.state.verbosity) + 0.5))  # round half up

    def _unrevealed(self, pool: list[InfoUnit]) -> list[InfoUnit]:
        return [u for u in pool if u.id not in self.state.revealed]

    def _narrate(self, pool: list[InfoUnit], n: int, reason: str, recall_contamination: bool = False) -> Decision:
        """Pick up to n unrevealed units (central first, chronological order),
        possibly with one integrated false detail resurfacing."""
        fresh = self._unrevealed(pool)
        ordered = [u for u in fresh if u.centrality == Centrality.CENTRAL] + [
            u for u in fresh if u.centrality == Centrality.PERIPHERAL
        ]
        picked: list[InfoUnit] = []
        for u in ordered:
            if len(picked) == n:
                break
            if self._lies_about(u):  # skipped on purpose: an omission
                self._withheld.append(u.id)
            else:
                picked.append(u)
        units = [self._allowed(u) for u in picked]
        if recall_contamination:
            resurfacing = self._resurfacing_contamination()
            if resurfacing is not None:
                units.append(resurfacing)
                reason += " + faux détail intégré"
        if not units:
            cover = self._untold_cover_story([u for u in pool if self._hidden.get(u.id)])
            if cover is not None:
                return self._lie(LieKind.COVER_STORY, cover.covers[0], f"{reason} : version de couverture", cover)
            return Decision(speech_act=SpeechAct.DONT_KNOW, reason=f"{reason} : plus rien à raconter")
        return Decision(speech_act=SpeechAct.ANSWER, allowed_units=units, reason=f"{reason} : {len(units)} unité(s)")

    def _resurfacing_contamination(self) -> AllowedUnit | None:
        integrated = [cu for cu in self.state.contaminated if cu.integrated]
        if not integrated or not self._draw(self.params["p_contamination_recall"]):
            return None
        cu = min(integrated, key=lambda x: (x.times_said, x.source_turn))
        cu.times_said += 1
        return AllowedUnit(id=cu.id, value=cu.value, contaminated=True, new=False)

    def _topic(self, c: Classification) -> EventKind | None:
        """Which event an open prompt is about, from the utterance's phase hint.
        None means rapport chit-chat. Default (no hint): the target event."""
        hint = c.phase_hints[0] if c.phase_hints else None
        if hint in ("rapport", "ground_rules"):
            return None
        if hint == "narrative_practice" and self.scenario.neutral_event is not None:
            return EventKind.NEUTRAL
        return EventKind.TARGET

    def _segment_pool(self, unit_id: str | None) -> tuple[EventKind, list[InfoUnit], str] | None:
        loc = self.scenario.locate(unit_id) if unit_id else None
        if loc is None:
            return None
        kind, segment = loc
        event = self.scenario.event(kind)
        pool = [u for s, u in event.units() if s == segment]
        return kind, pool, str(segment)

    def _invitation(self, c: Classification, t: QuestionType, topic=_FROM_HINT) -> Decision:
        if topic is _FROM_HINT:
            topic = self._topic(c)
            if topic == EventKind.TARGET and c.phase_hints[:1] == ["closure"]:
                return self._anything_else()
        if topic is None:
            return Decision(speech_act=SpeechAct.SMALL_TALK, reason="invitation de rapport")
        fresh = self._unrevealed(self._orders[topic])
        central_left = [u for u in fresh if u.centrality == Centrality.CENTRAL]
        # Hidden central facts do not count as "left to tell": the child moves on to peripheral ones.
        pool = central_left if self._visible(central_left) else fresh
        label = "invitation" if topic == EventKind.TARGET else "invitation (événement neutre)"
        return self._narrate(pool, self._invitation_size(), label, recall_contamination=topic == EventKind.TARGET)

    def _anything_else(self) -> Decision:
        """Closure « autre chose ? »: maybe one remaining central unit."""
        remaining = [
            u for u in self._visible(self._unrevealed(self._orders[EventKind.TARGET]))
            if u.centrality == Centrality.CENTRAL
        ]
        if not remaining:
            hidden = [
                u.id for u in self._unrevealed(self._orders[EventKind.TARGET])
                if u.centrality == Centrality.CENTRAL and self._hidden.get(u.id)
            ]
            self._withheld += hidden[:1]
        if remaining and self._draw(self.params["p_closure_reveal"]):
            return Decision(
                speech_act=SpeechAct.ANSWER,
                allowed_units=[self._allowed(remaining[0])],
                reason="clôture « autre chose ? » → une unité centrale restante",
            )
        return Decision(speech_act=SpeechAct.DENY, reason="clôture « autre chose ? » → non, c'est tout")

    def _cued_invitation(self, c: Classification, t: QuestionType) -> Decision:
        found = self._segment_pool(c.target)
        if found is None or not self._unrevealed(found[1]):
            return self._invitation(c, t, topic=found[0] if found else _FROM_HINT)
        kind, pool, segment = found
        return self._narrate(
            pool, self._invitation_size(), f"invitation indicée (segment {segment})",
            recall_contamination=kind == EventKind.TARGET,
        )

    def _facilitator(self, c: Classification, t: QuestionType) -> Decision:
        found = self._segment_pool(self.state.last_unit)
        if found is not None and self._unrevealed(found[1]):
            return self._narrate(found[1], 1, "facilitateur (suite du segment)")
        kind = found[0] if found else (self._topic(c) or EventKind.TARGET)
        return self._narrate(self._orders[kind], 1, "facilitateur")

    # -- focused questions --------------------------------------------------

    def _target_unit(self, c: Classification) -> InfoUnit | None:
        if not c.target or c.target == OUT_OF_SCENARIO:
            return None
        return self.scenario.unit(c.target)

    def _directive(self, c: Classification, t: QuestionType) -> Decision:
        unit = self._target_unit(c)
        if unit is not None and self._lies_about(unit):
            return self._lie_to_focused(unit, LieKind.FEIGNED_IGNORANCE, "question directive")
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
        if correct is not None and self._lies_about(unit):
            return self._lie_to_focused(unit, LieKind.FEIGNED_IGNORANCE, "question à choix")
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
        if unit is not None and (prop is None or proposition_matches(unit, prop)) and self._lies_about(unit):
            return self._lie_to_focused(unit, LieKind.FALSE_DENY, "question oui/non vraie")
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
        if unit is not None and (prop is None or proposition_matches(unit, prop)) and self._lies_about(unit):
            return self._lie_to_focused(unit, LieKind.FALSE_DENY, "suggestion tombée juste")
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

    # -- deception (ADR 0002) --------------------------------------------------

    def _active_lie(self, unit_id: str) -> LieRecord | None:
        """The standing (not retracted, not an omission) lie about a protected unit."""
        return next(
            (
                lr for lr in self.state.lies
                if lr.protected == unit_id and lr.retracted_turn is None and lr.kind != LieKind.OMISSION
            ),
            None,
        )

    def _lies_about(self, unit: InfoUnit) -> bool:
        """Does the child hide or disguise this fact now? Consistent with earlier lies and truths."""
        if not self.scenario.is_protected(unit.id) or unit.id in self.state.revealed:
            return False
        if self._active_lie(unit.id) is not None:
            return True  # a lie is only given up by a retraction
        self._hidden[unit.id] = self.state.concealment > self._thresholds[unit.id]
        return self._hidden[unit.id]

    def _visible(self, units: list[InfoUnit]) -> list[InfoUnit]:
        """Units the child is willing to mention in a narrative (protected ones may be omitted)."""
        return [u for u in units if not self._lies_about(u)]

    def _cover_story(self, unit_id: str) -> LieUnit | None:
        """The cover story for a fact, unless one of the facts it covers was already told truthfully."""
        cover = self.scenario.cover_story_for(unit_id)
        if cover is None or any(cid in self.state.revealed for cid in cover.covers):
            return None
        return cover

    def _untold_cover_story(self, hidden: list[InfoUnit]) -> LieUnit | None:
        told = {lr.lie_unit for lr in self.state.lies}
        for u in hidden:
            cover = self._cover_story(u.id)
            if cover is not None and cover.id not in told:
                return cover
        return None

    def _lie(self, kind: LieKind, protected: str, reason: str, content: LieUnit | None = None) -> Decision:
        """A lie decision; the LieRecord is completed (turn, type) by _record_deception."""
        if content is not None:
            act, units = SpeechAct.ANSWER, [AllowedUnit(id=content.id, value=content.value, lie=True)]
            value = content.value
        elif kind == LieKind.FALSE_DENY:
            act, units, value = SpeechAct.DENY, [], "non"
        else:
            act, units, value = SpeechAct.DONT_KNOW, [], "je sais pas"
        record = LieRecord(
            id="", kind=kind, protected=protected, lie_unit=content.id if content else None,
            value=value, turn=self.state.turn, question_type=QuestionType.OTHER,
        )
        return Decision(speech_act=act, allowed_units=units, lie=record, reason=f"{reason} → mensonge ({kind})")

    def _lie_to_focused(self, unit: InfoUnit, default: LieKind, reason: str) -> Decision:
        """Lie to a focused question about a protected fact: keep the standing lie, else the
        softest authored content (minimization, then cover story), else `default`."""
        standing = self._active_lie(unit.id)
        if standing is not None:
            content = self.scenario.lie_unit(standing.lie_unit) if standing.lie_unit else None
            return self._lie(standing.kind, unit.id, f"{reason} sur {unit.id} (mensonge maintenu)", content)
        mini = self.scenario.minimization_for(unit.id)
        if mini is not None:
            return self._lie(LieKind.MINIMIZATION, unit.id, f"{reason} sur {unit.id}", mini)
        cover = self._cover_story(unit.id)
        if cover is not None:
            return self._lie(LieKind.COVER_STORY, unit.id, f"{reason} sur {unit.id}", cover)
        return self._lie(default, unit.id, f"{reason} sur {unit.id}")

    def _record_deception(self, d: Decision, t: QuestionType) -> Decision:
        """Log the lie told and the omissions made at this turn."""
        st = self.state
        update: dict = {}
        if d.lie is not None:
            standing = self._active_lie(d.lie.protected)
            if standing is not None and standing.kind == d.lie.kind and standing.lie_unit == d.lie.lie_unit:
                standing.times += 1
                update["lie"] = standing.model_copy()
            else:
                record = d.lie.model_copy(update={"id": f"l{len(st.lies) + 1}", "question_type": t})
                st.lies.append(record)
                update["lie"] = record.model_copy()
        withheld = [uid for uid in dict.fromkeys(self._withheld) if d.lie is None or uid != d.lie.protected]
        if withheld:
            update["withheld"] = withheld
            for uid in withheld:
                if not any(lr.protected == uid and lr.kind == LieKind.OMISSION for lr in st.lies):
                    st.lies.append(
                        LieRecord(
                            id=f"l{len(st.lies) + 1}", kind=LieKind.OMISSION, protected=uid,
                            value="(omis)", turn=st.turn, question_type=t,
                        )
                    )
        return d.model_copy(update=update) if update else d

    def _maybe_retract(self, t: QuestionType) -> Decision | None:
        """Low concealment + a supportive or open prompt: the child may take back a lie."""
        st, p = self.state, self.params
        if self.scenario.deception is None or t not in (
            QuestionType.SUPPORT, QuestionType.INVITATION, QuestionType.CUED_INVITATION, QuestionType.FACILITATOR
        ):
            return None
        standing = [
            lr for lr in st.lies
            if lr.kind != LieKind.OMISSION and lr.retracted_turn is None and lr.protected not in st.revealed
        ]
        if not standing or st.concealment >= p["retraction_threshold"]:
            return None
        if self.deception_rng.random() >= p["p_retraction"]:
            return None
        lie = standing[0]
        covered = self.scenario.lie_unit(lie.lie_unit).covers if lie.lie_unit else [lie.protected]
        units = [self._allowed(u) for uid in covered if (u := self.scenario.unit(uid)) and uid not in st.revealed]
        for lr in st.lies:  # the truth is out: every lie about these facts is retracted
            if lr.protected in covered and lr.retracted_turn is None and lr.kind != LieKind.OMISSION:
                lr.retracted_turn = st.turn
        return Decision(
            speech_act=SpeechAct.RETRACT,
            allowed_units=units,
            retraction=lie.model_copy(update={"retracted_turn": st.turn}),
            reason=f"dissimulation {st.concealment:.2f} < seuil → revient sur {lie.id} ({lie.kind})",
        )

    # -- delivery (ADR 0002) ---------------------------------------------------

    def _with_delivery(self, d: Decision, c: Classification, about_target: bool) -> Decision:
        loads = self._hesitation_loads(d, c, about_target)
        delivery = make_delivery(loads, self.params, self.delivery_rng, speaks=d.speech_act != SpeechAct.SILENCE)
        return d.model_copy(update={"delivery": delivery})

    def _hesitation_loads(self, d: Decision, c: Classification, about_target: bool) -> dict[HesitationCause, float]:
        p, st = self.params, self.state
        true_units = [
            (au, unit) for au in d.allowed_units
            if not au.contaminated and (unit := self.scenario.unit(au.id)) is not None
        ]
        # Memory retrieval: the hardest unit said, eased when it was already said.
        act_load = p["retrieval_act_load"]
        if str(d.speech_act) in act_load:
            retrieval = act_load[str(d.speech_act)]
        else:
            retrieval = 0.0
            for au, unit in true_units:
                load = p["retrieval_difficulty"].get(str(unit.category), 0.3)
                if unit.centrality == Centrality.PERIPHERAL:
                    load += p["retrieval_peripheral_bonus"]
                retrieval = max(retrieval, load if au.new else load * 0.3)
        retrieval *= p["retrieval_age_factor"]
        # Emotion: talking about the target event, more so its central facts and when reluctant.
        target = [unit for _, unit in true_units if self.scenario.is_target_unit(unit.id)]
        if d.speech_act == SpeechAct.RELUCTANT or any(u.centrality == Centrality.CENTRAL for u in target):
            weight = 1.0
        elif target or d.lie is not None or (
            about_target and d.speech_act in (SpeechAct.DENY, SpeechAct.DONT_KNOW, SpeechAct.ACQUIESCE)
        ):
            weight = 0.5
        else:
            weight = 0.0
        affect = weight * (p["affect_base"] + (1 - p["affect_base"]) * st.reluctance)
        # Confusion: hard-to-parse questions.
        conf = p["confusion_load"]
        confusion = 0.0
        if d.speech_act == SpeechAct.CONFUSION:
            confusion = conf["confusion"]
        elif c.type == QuestionType.COMPOUND:
            confusion = conf["compound"]
        elif c.options and len(c.options) >= 3:
            confusion = conf["many_options"]
        deception = 0.0
        if d.lie is not None:
            deception = p["deception_load"][str(d.lie.kind)]
            if d.lie.times > 1:  # a rehearsed lie costs less
                deception *= p["rehearsed_lie_factor"]
        elif d.withheld:
            deception = p["deception_load"][str(LieKind.OMISSION)]
        return {
            HesitationCause.RETRIEVAL: retrieval,
            HesitationCause.AFFECT: affect,
            HesitationCause.CONFUSION: confusion,
            HesitationCause.DECEPTION: deception,
        }

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
            if not au.contaminated and not au.lie and au.id not in self.state.revealed:
                self.state.revealed.append(au.id)
                if self.scenario.is_target_unit(au.id):
                    self.state.disclosed = True
        true_units = [au for au in decision.allowed_units if not au.contaminated and not au.lie]
        if true_units:
            self.state.last_unit = true_units[-1].id
