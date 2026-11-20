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

from nichd_sim.classification import OUT_OF_SCENARIO, Classification, GroundRuleKind, PracticeKind, QuestionType
from nichd_sim.delivery import Delivery, HesitationCause, express, make_delivery
from nichd_sim.demeanor import Demeanor, make_demeanor
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import Centrality, EventKind, ExpressionStyle, InfoUnit, LieUnit, Scenario
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
    AFFIRM = "affirm"
    """« Oui » to a « do you know / remember…? » question, without the information it implies."""
    LEAK = "leak"
    """Asked again about a fact it lied about, the child lets the truth slip out, without taking the
    lie back (Talwar & Lee, 2002; Talwar et al., 2007): the lie and the fact now contradict."""


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
    leaked_turn: int | None = None
    """Turn at which the child let slip the true fact this lie hides (speech act `leak`)."""


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
    leak: LieRecord | None = None
    """The lie this turn's slip contradicts (speech act `leak`)."""
    demeanor: Demeanor | None = None
    """What the child's body shows (ADR 0003). None in logs older than format 3."""


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
    arousal: float = 0.0
    """Emotional arousal (0–1, ADR 0003), with inertia. Drives delivery and demeanor, not decisions."""
    arousal_baseline: float = 0.0
    """Level the arousal returns to, turn after turn."""
    last_act: SpeechAct | None = None
    """The child's speech act at the previous turn (how the interviewer reacts to it matters)."""
    last_target: str | None = None
    """What the previous prompt targeted (info unit id, or OUT_OF_SCENARIO)."""
    closed_asked: dict[str, int] = {}
    """How many times each closed question was asked (key: see `closed_key`)."""
    last_key: str | None = None
    """Closed-question key of the previous prompt (None if it was open)."""
    supports_given: int = 0
    """Support statements counted for their effect on acquiescence (capped)."""
    promised: bool = False
    """The child promised to tell the truth (its effect on concealment counts once)."""
    expressivity: float = 0.0
    """How much the child dares to show what it feels (0–1, ADR 0003 addendum): raised by support
    and rapport, lowered by pressure. Body only, like arousal."""


_CLOSED = {QuestionType.DIRECTIVE, QuestionType.OPTION_POSING, QuestionType.SUGGESTIVE}


def effective_type(c: Classification) -> QuestionType:
    """The type the engine acts on: a compound question's most directive part; a « why » closed
    question is really an open one (« pourquoi… ? » is never answered by a bare yes or no)."""
    t = (c.inner_type or QuestionType.DIRECTIVE) if c.type == QuestionType.COMPOUND else c.type
    if c.causal and t == QuestionType.OPTION_POSING and not c.options:
        return QuestionType.DIRECTIVE
    return t


def closed_key(c: Classification, effective: QuestionType, utterance: str | None) -> str | None:
    """Identity of a closed question, to count repetitions: the targeted unit, or, for a detail
    absent from the scenario, the question's normalized wording. None for open prompts."""
    if effective not in _CLOSED:
        return None
    if c.target and c.target != OUT_OF_SCENARIO:
        return c.target
    return f"{OUT_OF_SCENARIO}:{normalize(utterance or c.suggested_proposition or '')}"


REFUSAL_ACTS = {SpeechAct.DONT_KNOW, SpeechAct.RELUCTANT, SpeechAct.DENY}
"""Avoidance and denial: « je sais pas », not ready to talk, « non ». How the interviewer reacts to
them changes what the child says next (Bücken et al., 2026)."""


def is_rejection(prev_act: SpeechAct | None, prev_key: str | None, key: str | None) -> bool:
    """The interviewer asks the same closed question again after the child avoided or denied it."""
    return prev_act in REFUSAL_ACTS and key is not None and key == prev_key


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
        self.demeanor_rng = random.Random(f"{seed}:demeanor")
        self.dynamics_rng = random.Random(f"{seed}:dynamics")
        """Draws of the interaction dynamics (reaction to « je sais pas », repetitions — plan lot 1)."""
        self.prev_act: SpeechAct | None = None
        self.prev_target: str | None = None
        self.asked_before = 0
        self.rejection = False
        self._acq_boost = 0.0
        """Extra acquiescence for this turn only (after a rejected « je sais pas »)."""
        protected = scenario.deception.protected if scenario.deception else []
        draws = sorted((self.deception_rng.random() for _ in protected), reverse=True)
        self._thresholds = dict(zip(protected, draws))
        """Per protected fact, drawn once: the fact stays hidden while concealment exceeds it.
        Facts come out one by one as support lowers concealment (pressure hides them again), in
        the authored order: `protected` lists them from least to most guarded."""
        self._hidden: dict[str, bool] = {}
        """Per-turn concealment draws, so that a unit is hidden or not consistently within a turn."""
        profile = scenario.child_profile
        self.style = profile.expression_style or ExpressionStyle(params["expression_style_default"])
        baseline = round(min(1.0, params["arousal_base"] + params["arousal_reluctance_weight"] * profile.reluctance), 6)
        self.state = EngineState(
            reluctance=profile.reluctance,
            verbosity=profile.verbal_skills,
            acquiescence=profile.suggestibility,
            concealment=scenario.deception.strength if scenario.deception else 0.0,
            arousal=baseline,
            arousal_baseline=baseline,
        )
        self._phase_violation = False
        self._near_disclosure = False
        self._waiting = False
        self._orders: dict[EventKind, list[InfoUnit]] = {
            EventKind.TARGET: [u for _, u in scenario.target_units()],
            EventKind.NEUTRAL: [u for _, u in scenario.neutral_units()],
        }

    # -- public -------------------------------------------------------------

    def decide(
        self, c: Classification, *, phase_violation: bool = False, utterance: str | None = None, wait: bool = False
    ) -> Decision:
        """`phase_violation`: the phase tracker flagged this prompt (it raises the child's arousal).
        `utterance`: the prompt as the child heard it (identifies repeated questions).
        `wait`: no prompt at all, the interviewer lets a silence run on (plan, lot 5)."""
        effective = effective_type(c)
        key = closed_key(c, effective, utterance)
        st = self.state
        self.prev_act, self.prev_target = st.last_act, st.last_target
        self.asked_before = st.closed_asked.get(key, 0) if key else 0
        """How many times this closed question was already asked (0: first time, or open prompt)."""
        self.rejection = is_rejection(st.last_act, st.last_key, key)
        self._acq_boost = 0.0
        self._react_to_refusal()
        self._waiting = wait
        decision = self._decide(c, phase_violation)
        if key:
            st.closed_asked = {**st.closed_asked, key: self.asked_before + 1}
        st.last_act, st.last_target, st.last_key = decision.speech_act, c.target, key
        return decision

    def _react_to_refusal(self) -> None:
        """After « je sais pas » or « non »: asking it again (rejection) makes the child more
        reluctant and, for this turn, more compliant; moving on (acceptance) reassures."""
        st, p = self.state, self.params
        if self.prev_act not in REFUSAL_ACTS:
            return
        if self.rejection:
            if p["rejection_reluctance_rise"]:
                st.reluctance = round(min(1.0, st.reluctance + p["rejection_reluctance_rise"]), 6)
            self._acq_boost = p["rejection_acquiescence_boost"]
        elif p["acceptance_reluctance_drop"]:
            st.reluctance = round(max(0.0, st.reluctance - p["acceptance_reluctance_drop"]), 6)

    def _decide(self, c: Classification, phase_violation: bool) -> Decision:
        self.state.turn += 1
        self._phase_violation = phase_violation
        self._near_disclosure = False
        self._hidden = {}
        self._withheld: list[str] = []
        effective = effective_type(c)
        self._apply_phase_effects(c, effective)
        was_disclosed = self.state.disclosed
        about_target = self._about_target(c, effective)
        if self._waiting:
            decision = self._wait(c).model_copy(update={"effective_type": effective})
            decision = self._record_deception(decision, effective)
            self._commit(decision)
            return self._with_delivery(decision, c, about_target)
        if not was_disclosed and about_target:
            gate = self._disclosure_gate(effective)
            if effective in (QuestionType.SUGGESTIVE, QuestionType.OPTION_POSING) and self.params["pressure_reluctance_rise"]:
                # Pressure before disclosure: a reluctant child closes up (Hershkowitz et al., 2006).
                st = self.state
                st.reluctance = round(min(1.0, st.reluctance * (1 + self.params["pressure_reluctance_rise"])), 6)
            if gate is not None:
                decision = gate.model_copy(update={"effective_type": effective})
                self._commit(decision)
                return self._with_delivery(decision, c, about_target)
        retraction = self._maybe_retract(effective)
        if retraction is not None:
            decision = retraction.model_copy(update={"effective_type": effective})
            self._commit(decision)
            return self._with_delivery(decision, c, about_target)
        if c.knowledge_question and effective in (QuestionType.OPTION_POSING, QuestionType.DIRECTIVE) and not c.options:
            decision = self._knowledge_question(c, effective).model_copy(update={"effective_type": effective})
            decision = self._record_deception(decision, effective)
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
            if st.supports_given < p["max_effective_supports"] and p["support_acquiescence_drop"]:
                st.supports_given += 1
                st.acquiescence = round(max(0.0, st.acquiescence - p["support_acquiescence_drop"]), 6)
        elif t == QuestionType.INVITATION and hint == "rapport":
            st.reluctance = max(0.0, st.reluctance - p["rapport_reluctance_drop"])
        elif (
            t == QuestionType.GROUND_RULE
            and st.ground_rules_given < p["max_effective_ground_rules"]
            and c.ground_rule_kind not in (GroundRuleKind.TRUTH, GroundRuleKind.PROMISE)
        ):
            st.ground_rules_given += 1
            st.acquiescence = max(0.0, st.acquiescence - p["ground_rule_acquiescence_drop"] * self._ground_rule_factor(c))
        if self.scenario.deception is not None:
            if t == QuestionType.SUPPORT:
                st.concealment -= p["support_concealment_drop"]
            elif t == QuestionType.INVITATION and hint == "rapport":
                st.concealment -= p["rapport_concealment_drop"]
            elif (
                t == QuestionType.GROUND_RULE and c.ground_rule_kind == GroundRuleKind.PROMISE
                and not st.promised and p["promise_concealment_drop"]
            ):
                # Promising to tell the truth lowers lying about an adult's fault (Talwar et al., 2004).
                st.promised = True
                st.concealment -= p["promise_concealment_drop"]
            elif t in (QuestionType.SUGGESTIVE, QuestionType.OPTION_POSING) and self.scenario.is_protected(c.target):
                st.concealment += p["pressure_concealment_rise"]
            st.concealment = round(min(1.0, max(0.0, st.concealment)), 6)
        if (
            t in (QuestionType.INVITATION, QuestionType.CUED_INVITATION)
            and hint == "narrative_practice"
            and st.practice_turns < p["max_effective_practice_turns"]
            and (c.practice_kind != PracticeKind.GENERIC or p["generic_practice_counts"])
        ):
            st.practice_turns += 1
            st.verbosity = min(1.0, st.verbosity + p["narrative_practice_verbosity_boost"])

    def _ground_rule_factor(self, c: Classification) -> float:
        """A rule only stated barely changes answers in the field (Earhart et al., 2014); practising it
        does, less so for the youngest (Brubacher et al., 2015). Unknown kind (older classifier): 1."""
        if c.ground_rule_kind is None:
            return 1.0
        if c.ground_rule_kind == GroundRuleKind.PRACTICE:
            return self.params["ground_rule_age_factor"]
        return self.params["ground_rule_stated_factor"]

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
        # Close to telling: the body shows it before the words (Karni-Visel et al., 2023).
        self._near_disclosure = st.disclosure_pressure >= p["pre_disclosure_fraction"] * threshold
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
        return lo + (hi - lo) * min(1.0, self.state.acquiescence + self._acq_boost)

    def _p(self, name: str, modulated: bool = False) -> float:
        p = self.params[name] * (self._suggestibility_factor() if modulated else 1.0)
        return min(1.0, max(0.0, p))

    def _draw(self, p: float) -> bool:
        return self.rng.random() < p

    def _dyn_draw(self, p: float) -> bool:
        """A draw of the interaction dynamics, in its own stream; none at all when the rule is off."""
        return p > 0 and self.dynamics_rng.random() < p

    # -- open questions -----------------------------------------------------

    def _invitation_size(self) -> int:
        base = self.params["units_per_invitation"]
        lo, hi = self.params["verbosity_multiplier_range"]
        size = base * (lo + (hi - lo) * self.state.verbosity)
        weight = self.params["reluctance_informativeness_weight"]
        if not weight:
            return max(1, int(size + 0.5))  # round half up
        # A reluctant child tells less (Blasbalg et al., 2018); stochastic rounding keeps small effects.
        size *= 1 - weight * self.state.reluctance
        whole = int(size)
        return max(1, whole + (1 if self.dynamics_rng.random() < size - whole else 0))

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
        if c.segment is not None:  # « raconte-moi la fin »: that part of the event only
            return self._narrate(self._time_segment(topic, c.segment), self._invitation_size(),
                                 f"invitation (segment {c.segment})", recall_contamination=topic == EventKind.TARGET)
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

    def _time_segment(self, kind: EventKind, segment: str) -> list[InfoUnit]:
        return [u for s, u in self.scenario.event(kind).units() if str(s) == str(segment)]

    def _cued_invitation(self, c: Classification, t: QuestionType) -> Decision:
        if c.segment is not None:
            kind = self._topic(c) or EventKind.TARGET
            return self._narrate(self._time_segment(kind, c.segment), self._invitation_size(),
                                 f"invitation indicée (segment {c.segment})")
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

    def _wait(self, c: Classification) -> Decision:
        """A silence after the child's answer: it often goes on with what it was telling (Rezmer et
        al., 2020), like after a facilitator; otherwise it stays silent. It never opens a disclosure:
        before one, there is nothing about the event under way to go on with."""
        silent = Decision(speech_act=SpeechAct.SILENCE, reason="attente → l'enfant reste silencieux")
        if self.state.last_unit is None or not self._dyn_draw(self.params["p_wait_elaboration"]):
            return silent
        d = self._facilitator(c, QuestionType.FACILITATOR)
        if d.speech_act != SpeechAct.ANSWER:
            return silent.model_copy(update={"reason": "attente → plus rien à ajouter"})
        return d.model_copy(update={"reason": "attente → " + d.reason})

    # -- focused questions --------------------------------------------------

    def _knowledge_question(self, c: Classification, t: QuestionType) -> Decision:
        """« Est-ce que tu sais / te souviens… ? »: often a bare « oui », more so for the youngest
        (Evans et al., 2014, 2017); otherwise the child answers the implied wh- question."""
        unit = self._target_unit(c)
        if not (unit is not None and self._lies_about(unit)) and self._dyn_draw(self.params["p_unelaborated_yes"]):
            return Decision(speech_act=SpeechAct.AFFIRM, reason="« est-ce que tu sais… ? » → oui, sans détail")
        return self._directive(c, QuestionType.DIRECTIVE)

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
        gain = self.params["repeat_confabulation_gain"] ** self.asked_before  # Krähenbühl et al. (2009)
        if self._draw(min(1.0, self._p("p_confabulation", modulated=True) * gain)):
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
        changed = correct is not None and self.asked_before > 0 and self._dyn_draw(self.params["p_change_on_repeat"])
        if correct is not None and not changed and self._draw(self.params["p_correct_option"]):
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
            if self.asked_before > 0 and self._dyn_draw(self.params["p_change_on_repeat"]):
                # Asked again: the child takes it the first answer was wrong (Krähenbühl et al., 2009).
                return Decision(speech_act=SpeechAct.DENY, reason="question oui/non vraie répétée → change de réponse")
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
        if standing is not None and self._leaks():
            standing.leaked_turn = self.state.turn
            return Decision(
                speech_act=SpeechAct.LEAK,
                allowed_units=[self._allowed(unit)],
                leak=standing.model_copy(),
                reason=f"{reason} sur {unit.id} : la vérité échappe, contredit {standing.id} ({standing.kind})",
            )
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

    def _leaks(self) -> bool:
        """A follow-up question on a lie: the younger the child, the likelier the truth slips out."""
        p = self.params["p_leak"]
        return p > 0 and self.deception_rng.random() < p

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
        """Delivery (ADR 0002) and demeanor (ADR 0003): how the child says it and what its body shows."""
        self._update_arousal(d, c, about_target)
        speaks = d.speech_act != SpeechAct.SILENCE
        loads = self._hesitation_loads(d, c, about_target)
        delivery = make_delivery(loads, self.params, self.delivery_rng, speaks=speaks)
        motor = self.params["expression_gains"][str(self.style)]["motor"]
        delivery = express(delivery, self.state.arousal, motor, self.params, self.demeanor_rng, speaks=speaks)
        demeanor = make_demeanor(
            self.state.arousal, delivery.loads, self.style, self.params, self.demeanor_rng,
            sociable=d.speech_act in (SpeechAct.SMALL_TALK, SpeechAct.ACKNOWLEDGE),
            expressivity=self.state.expressivity, reluctance=self.state.reluctance,
        )
        return d.model_copy(update={"delivery": delivery, "demeanor": demeanor})

    def _update_arousal(self, d: Decision, c: Classification, about_target: bool) -> None:
        """Arousal: back toward the baseline, then up with the target event and pressure, down with
        support. A hidden fact (lie, omission) weighs like the truth it hides; the lie itself adds
        only a weak rise, so that the body does not give it away (ADR 0003)."""
        st, p = self.state, self.params
        rise, drop = p["arousal_rise"], p["arousal_drop"]
        a = st.arousal_baseline + (st.arousal - st.arousal_baseline) * (1.0 - p["arousal_decay"])
        t = d.effective_type or c.type
        hint = c.phase_hints[0] if c.phase_hints else None
        ups: list[float] = []
        if t == QuestionType.SUPPORT:
            a -= drop["support"]
        elif t == QuestionType.INVITATION and hint == "rapport":
            a -= drop["rapport"]
        elif t in (QuestionType.INVITATION, QuestionType.CUED_INVITATION) and hint == "narrative_practice":
            a -= drop["narrative_practice"]
        elif t in (QuestionType.SUGGESTIVE, QuestionType.OPTION_POSING):
            ups.append(rise["pressure_target"] if about_target else rise["pressure"])
        if self._phase_violation:
            ups.append(rise["phase_violation"])
        if self._near_disclosure and p["pre_disclosure_rise"]:
            ups.append(p["pre_disclosure_rise"])
        self._update_expressivity(t, hint)
        ids = [au.id for au in d.allowed_units if not au.contaminated and not au.lie] + list(d.withheld)
        if d.lie is not None:
            ids.append(d.lie.protected)
        units = [u for i in ids if (u := self.scenario.unit(i)) is not None and self.scenario.is_target_unit(i)]
        if any(u.centrality == Centrality.CENTRAL for u in units):
            ups.append(rise["target_central"])
        elif units or (
            about_target
            and d.speech_act in (SpeechAct.DENY, SpeechAct.DONT_KNOW, SpeechAct.ACQUIESCE, SpeechAct.RELUCTANT)
        ):
            ups.append(rise["target_other"])
        if d.lie is not None or d.withheld:
            ups.append(rise["lie"])
        a = max(0.0, min(1.0, a))
        for up in ups:
            a += up * (1.0 - a)
        st.arousal = round(min(1.0, max(0.0, a)), 6)

    def _update_expressivity(self, t: QuestionType, hint: str | None) -> None:
        """Support and rapport make the child dare to show its emotion (Karni-Visel et al., 2023)."""
        change = self.params["expressivity_change"]
        if t == QuestionType.SUPPORT:
            delta = change["support"]
        elif t == QuestionType.INVITATION and hint == "rapport":
            delta = change["rapport"]
        elif t in (QuestionType.SUGGESTIVE, QuestionType.OPTION_POSING):
            delta = change["pressure"]
        else:
            return
        if delta:
            st = self.state
            st.expressivity = round(min(1.0, max(0.0, st.expressivity + delta)), 6)

    def _hesitation_loads(self, d: Decision, c: Classification, about_target: bool) -> dict[HesitationCause, float]:
        p, st = self.params, self.state
        true_units = [
            (au, unit) for au in d.allowed_units
            if not au.contaminated and (unit := self.scenario.unit(au.id)) is not None
        ]
        # Memory retrieval: the hardest unit said, eased when it was already said.
        def difficulty(unit: InfoUnit, new: bool) -> float:
            load = p["retrieval_difficulty"].get(str(unit.category), 0.3)
            if unit.centrality == Centrality.PERIPHERAL:
                load += p["retrieval_peripheral_bonus"]
            return load if new else load * 0.3

        act_load = p["retrieval_act_load"]
        hidden = self.scenario.unit(d.lie.protected) if d.lie is not None else None
        if hidden is not None:
            # Lying about a fact means recalling it too: same retrieval load as telling it, so that
            # only the deception load tells a lie from the truth (ADR 0002, voice evaluation N2).
            retrieval = difficulty(hidden, d.lie.times == 1)
        elif str(d.speech_act) in act_load:
            retrieval = act_load[str(d.speech_act)]
        else:
            retrieval = max((difficulty(unit, au.new) for au, unit in true_units), default=0.0)
        retrieval *= p["retrieval_age_factor"]
        # Emotion: talking about the target event, more so its central facts and when reluctant.
        target = [unit for _, unit in true_units if self.scenario.is_target_unit(unit.id)]
        if hidden is not None:
            # A lie is about the same painful fact as the truth it hides: same emotional load
            # (otherwise a fast answer would give the lie away — an inverted false cue).
            target.append(hidden)
        if d.speech_act == SpeechAct.RELUCTANT or any(u.centrality == Centrality.CENTRAL for u in target):
            weight = 1.0
        elif target or (
            about_target and d.speech_act in (SpeechAct.DENY, SpeechAct.DONT_KNOW, SpeechAct.ACQUIESCE)
        ):
            weight = 0.5
        else:
            weight = 0.0
        affect = weight * (p["affect_base"] + (1 - p["affect_base"]) * st.reluctance)
        # Arousal (ADR 0003) adds to the emotional load, even on neutral topics.
        affect = 1.0 - (1.0 - affect) * (1.0 - p["arousal_affect_weight"] * st.arousal)
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
