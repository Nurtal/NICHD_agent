"""Session facade: the single entry point used by the CLI, the UI and the tests."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel

from nichd_sim.classification import Classification, ClassificationContext, Classifier
from nichd_sim.delivery import SpeechChunk, plan_speech
from nichd_sim.engine import BehaviorEngine, Decision, EngineState, SpeechAct
from nichd_sim.feedback import FeedbackReport, Rephraser, SummaryMatcher, build_feedback
from nichd_sim.output_filter import OutputFilter
from nichd_sim.parameters import Parameters
from nichd_sim.phases import Phase, PhaseTracker, PhaseViolation, ViolationKind
from nichd_sim.realization import Realizer, TemplateRealizer
from nichd_sim.scenario import Scenario
from nichd_sim.text import mentions, normalize

MAX_REALIZATION_ATTEMPTS = 2  # first try + one regeneration, then fallback response

StepListener = Callable[[str, dict[str, Any]], None]
"""Called at each step of a turn (live display only): `classify`, `classified`, `decided`, `realize`,
`filtered`, `fallback`, `done`. It must not act on the session."""

SOFT_TURN_LIMIT = 60  # warn (never interrupt) once the interview reaches this many turns


class AttemptRecord(BaseModel):
    text: str
    prompt: str | None = None
    ok: bool
    forbidden_terms: list[str] = []
    leaked_units: list[str] = []
    missing_units: list[str] = []
    empty: bool = False
    too_long: bool = False
    contradicts: bool = False
    emoji: bool = False
    meta: dict = {}


class BargeIn(BaseModel):
    """The learner spoke before the end of the child's previous reply."""

    during: Literal["onset", "pause", "speech"]
    """`onset`: before the child started answering (initial silence or « euh »); `pause`: in a
    pause or a filler mid-reply; `speech`: while the child was talking."""
    at_ms: int
    """Offset in the child's reply audio where the learner started speaking."""
    heard_text: str
    """What the child had said before being cut off."""


class TurnTiming(BaseModel):
    """When the learner spoke (voice sessions only)."""

    wait_ms: int
    """Learner speech start − end of the child's previous reply audio (negative: interruption)."""
    barge_in: BargeIn | None = None
    speech_ms: int | None = None
    """Duration of the learner's utterance."""


class TurnRecord(BaseModel):
    index: int
    utterance: str
    classification: Classification
    asked_in: Phase
    """Phase when the interviewer spoke."""
    phase: Phase
    """Phase after the child's answer (a disclosure opens the substantive phase)."""
    state_before: EngineState
    decision: Decision
    state_after: EngineState
    attempts: list[AttemptRecord] = []
    fallback_used: bool = False
    response: str
    latency_s: dict[str, float] = {}
    timing: TurnTiming | None = None
    """When the learner asked this (voice sessions)."""
    heard_response: str | None = None
    """Set when the learner interrupted this reply: the part the child had time to say."""
    unheard_units: list[str] = []
    """Units of this reply cut off by the interruption (taken back by the engine)."""

    @property
    def prompt(self) -> str | None:
        return self.attempts[-1].prompt if self.attempts else None


LOG_FORMAT = 6
"""2: decisions carry a delivery (ADR 0002). 3: arousal and demeanor (ADR 0003); the delivery now
depends on arousal. 4: the engine remembers the previous turn and the closed questions asked, and
parameters added since carry a neutral value (docs/plans/adaptations-litterature.md). 5: the promise to tell
the truth and the slips of the truth (speech act `leak`). 6: expressivity (what the child dares
to show) and the body announcing a disclosure (ADR 0003 addendum). Older logs still
replay: decisions are compared, newer fields ignored, newer parameters neutral."""


class SessionLog(BaseModel):
    log_format: int = LOG_FORMAT
    session_id: str
    started_at: str
    ended_at: str | None = None
    scenario_id: str
    scenario_version: str
    seed: int
    parameters: dict
    components: dict[str, str]
    turns: list[TurnRecord] = []
    phase_violations: list[PhaseViolation] = []
    feedback: FeedbackReport | None = None


class TurnResult(BaseModel):
    """What one turn exposes: the child's response plus trainer-mode details."""

    response: str
    classification: Classification
    decision: Decision
    state: EngineState
    phase: Phase
    violations: list[PhaseViolation] = []
    """Phase violations detected at this turn."""
    notices: list[str] = []
    """Non-blocking messages for the learner (e.g. interview length)."""
    fallback_used: bool = False
    speech_plan: list[SpeechChunk] = []
    """The response cut into speech and silences according to the decision's delivery (voice, display)."""


class SessionEnded(RuntimeError):
    pass


class Session:
    def __init__(
        self,
        scenario: Scenario,
        classifier: Classifier,
        realizer: Realizer,
        *,
        seed: int = 0,
        params: Parameters | None = None,
        output_filter: OutputFilter | None = None,
        rephraser: Rephraser | None = None,
        summary_matcher: SummaryMatcher | None = None,
        log_dir: str | Path | None = None,
    ):
        self.scenario = scenario
        self.classifier = classifier
        self.realizer = realizer
        self.seed = seed
        self.params = params or Parameters.load(scenario.child_profile.age_band, scenario.parameter_overrides)
        self.output_filter = output_filter or OutputFilter(scenario)
        self.rephraser = rephraser
        self.summary_matcher = summary_matcher
        self.log_dir = Path(log_dir) if log_dir else None
        self.engine = BehaviorEngine(scenario, self.params, seed)
        self.phases = PhaseTracker(scenario)
        self.history: list[tuple[str, str]] = []
        self.log = SessionLog(
            session_id=uuid.uuid4().hex[:12],
            started_at=_now(),
            scenario_id=scenario.id,
            scenario_version=scenario.version,
            seed=seed,
            parameters=self.params.snapshot(),
            components={
                "classifier": _describe(classifier),
                "realizer": _describe(realizer),
                **({"skill_version": classifier.skill_version} if hasattr(classifier, "skill_version") else {}),
            },
        )
        self._ended = False

    @property
    def state(self) -> EngineState:
        return self.engine.state.model_copy(deep=True)

    def turn(
        self, utterance: str, timing: TurnTiming | None = None, on_step: StepListener | None = None
    ) -> TurnResult:
        """One interviewer utterance. `timing` (voice): when the learner spoke, and whether they
        interrupted the child's previous reply — the cut-off part was then not said.
        `on_step`: live display of the turn's progress (see `StepListener`); no effect on the turn."""
        emit = on_step or (lambda step, data: None)
        if self._ended:
            raise SessionEnded("la session est terminée")
        if timing is not None and timing.barge_in is not None and self.log.turns:
            self._interrupt(timing.barge_in)
        context = ClassificationContext(
            scenario=self.scenario,
            revealed_unit_ids=list(self.engine.state.revealed),
            history=list(self.history),
        )
        emit("classify", {"utterance": utterance})
        t0 = time.perf_counter()
        classification = self.classifier.classify(utterance, context)
        t1 = time.perf_counter()
        emit("classified", {"classification": classification})
        heard = classification.clean_text or utterance
        before = self.state
        n_violations = len(self.phases.violations)
        asked_in = self.phases.observe(classification)
        decision = self.engine.decide(
            classification, phase_violation=len(self.phases.violations) > n_violations, utterance=heard
        )
        phase = self.phases.after_decision(
            revealed_target=any(
                not u.contaminated and self.scenario.is_target_unit(u.id) for u in decision.allowed_units
            )
        )
        if decision.forced_disclosure:
            self.phases.flag(ViolationKind.FORCED_DISCLOSURE, detail=f"{decision.effective_type}")
        new_violations = self.phases.violations[n_violations:]
        emit("decided", {
            "decision": decision, "asked_in": asked_in, "phase": phase, "violations": list(new_violations),
            "state_before": before, "state_after": self.state,
        })

        history = self.history + [("interviewer", heard)]
        # The child may mention what it already said: true units, and the lies it told.
        known = before.revealed + [lr.lie_unit for lr in self.engine.state.lies if lr.lie_unit]
        attempts, response, fallback = self._realize(decision, history, known=known, emit=emit)
        if decision.speech_act == SpeechAct.CONFABULATE and decision.new_contamination:
            self.engine.record_confabulation(decision.new_contamination, response)
        after = self.state
        t2 = time.perf_counter()

        self.history = history + [("child", response)]
        self.log.turns.append(
            TurnRecord(
                index=len(self.log.turns) + 1,
                utterance=utterance,
                classification=classification,
                asked_in=asked_in,
                phase=phase,
                state_before=before,
                decision=decision,
                state_after=after,
                attempts=attempts,
                fallback_used=fallback,
                response=response,
                latency_s={
                    "classification": round(t1 - t0, 3),
                    "realization": round(t2 - t1, 3),
                    "total": round(t2 - t0, 3),
                },
                timing=timing,
            )
        )
        self.log.phase_violations = list(self.phases.violations)
        notices = []
        if len(self.log.turns) == SOFT_TURN_LIMIT:
            notices.append(
                f"L'entretien atteint {SOFT_TURN_LIMIT} tours : pensez à la durée et à la fatigue de l'enfant."
            )
        result = TurnResult(
            response=response,
            classification=classification,
            decision=decision,
            state=after,
            phase=phase,
            violations=new_violations,
            notices=notices,
            fallback_used=fallback,
            speech_plan=plan_speech(response, decision.delivery),
        )
        emit("done", {"result": result})
        return result

    def _interrupt(self, barge: BargeIn) -> None:
        """The previous reply was cut: keep what was heard, take back the units not said."""
        last = self.log.turns[-1]
        heard = normalize(barge.heard_text)
        unheard = []
        for au in last.decision.allowed_units:
            unit = self.scenario.unit(au.id)
            if au.contaminated or au.lie or not au.new or unit is None:
                continue
            if not any(mentions(heard, a) for a in unit.anchors):
                unheard.append(au.id)
        self.engine.unsay(unheard)
        last.heard_response = barge.heard_text
        last.unheard_units = unheard
        if self.history and self.history[-1][0] == "child":
            cut = barge.heard_text.strip()
            self.history[-1] = ("child", f"{cut} —" if cut else "…")

    @property
    def phase(self) -> Phase:
        return self.phases.phase

    def _realize(
        self, decision: Decision, history, known: list[str], emit: StepListener | None = None
    ) -> tuple[list[AttemptRecord], str, bool]:
        emit = emit or (lambda step, data: None)
        attempts: list[AttemptRecord] = []
        for attempt in range(MAX_REALIZATION_ATTEMPTS):
            emit("realize", {"attempt": attempt + 1})
            r = self.realizer.realize(decision, self.scenario.child_profile, list(history), attempt=attempt)
            verdict = self.output_filter.check(r.text, decision, known_unit_ids=known)
            emit("filtered", {"attempt": attempt + 1, "ok": verdict.ok, "text": r.text})
            attempts.append(
                AttemptRecord(
                    text=r.text,
                    prompt=r.prompt,
                    ok=verdict.ok,
                    forbidden_terms=verdict.forbidden_terms,
                    leaked_units=verdict.leaked_units,
                    missing_units=verdict.missing_units,
                    empty=verdict.empty,
                    too_long=verdict.too_long,
                    contradicts=verdict.contradicts,
                    emoji=verdict.emoji,
                    meta=r.meta,
                )
            )
            if verdict.ok:
                return attempts, r.text, False
        # Fallback: authored unit values / canned response — safe by construction.
        emit("fallback", {})
        fallback = TemplateRealizer().realize(decision, self.scenario.child_profile, list(history)).text
        return attempts, fallback, True

    def end(self, learner_summary: str | None = None) -> SessionLog:
        """End the session. `learner_summary`: optional account written by the learner."""
        if not self._ended:
            self._ended = True
            self.log.phase_violations = list(self.phases.finish())
            self.log.ended_at = _now()
            self.log.feedback = build_feedback(
                self.log, self.scenario, self.rephraser, learner_summary, self.summary_matcher
            )
            if self.log_dir is not None:
                self.write_log(self.log_dir)
        return self.log

    def write_log(self, directory: str | Path) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"session_{self.log.session_id}.json"
        path.write_text(self.log.model_dump_json(indent=2), encoding="utf-8")
        return path


def _describe(component) -> str:
    name = type(component).__name__
    client = getattr(component, "client", None)
    model = getattr(client, "model", None)
    think = getattr(component, "think", None)
    if think:
        model = f"{model}, réflexion {think}"
    return f"{name}({model})" if model else name


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
