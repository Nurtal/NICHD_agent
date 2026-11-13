"""Session facade: the single entry point used by the CLI, the UI and the tests."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from nichd_sim.classification import Classification, ClassificationContext, Classifier
from nichd_sim.engine import BehaviorEngine, Decision, EngineState, SpeechAct
from nichd_sim.output_filter import OutputFilter
from nichd_sim.parameters import Parameters
from nichd_sim.phases import Phase, PhaseTracker, PhaseViolation
from nichd_sim.realization import Realizer, TemplateRealizer
from nichd_sim.scenario import Scenario

MAX_REALIZATION_ATTEMPTS = 2  # first try + one regeneration, then fallback response


class AttemptRecord(BaseModel):
    text: str
    prompt: str | None = None
    ok: bool
    forbidden_terms: list[str] = []
    leaked_units: list[str] = []
    missing_units: list[str] = []
    empty: bool = False
    meta: dict = {}


class TurnRecord(BaseModel):
    index: int
    utterance: str
    classification: Classification
    phase: Phase
    state_before: EngineState
    decision: Decision
    state_after: EngineState
    attempts: list[AttemptRecord] = []
    fallback_used: bool = False
    response: str
    latency_s: dict[str, float] = {}

    @property
    def prompt(self) -> str | None:
        return self.attempts[-1].prompt if self.attempts else None


class SessionLog(BaseModel):
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


class TurnResult(BaseModel):
    """What one turn exposes: the child's response plus trainer-mode details."""

    response: str
    classification: Classification
    decision: Decision
    state: EngineState
    phase: Phase
    violations: list[PhaseViolation] = []
    """Phase violations detected at this turn."""
    fallback_used: bool = False


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
        log_dir: str | Path | None = None,
    ):
        self.scenario = scenario
        self.classifier = classifier
        self.realizer = realizer
        self.seed = seed
        self.params = params or Parameters.load(scenario.child_profile.age_band, scenario.parameter_overrides)
        self.output_filter = output_filter or OutputFilter(scenario)
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

    def turn(self, utterance: str) -> TurnResult:
        if self._ended:
            raise SessionEnded("la session est terminée")
        context = ClassificationContext(
            scenario=self.scenario,
            revealed_unit_ids=list(self.engine.state.revealed),
            history=list(self.history),
        )
        t0 = time.perf_counter()
        classification = self.classifier.classify(utterance, context)
        t1 = time.perf_counter()
        heard = classification.clean_text or utterance
        before = self.state
        n_violations = len(self.phases.violations)
        self.phases.observe(classification)
        decision = self.engine.decide(classification)
        phase = self.phases.after_decision(
            revealed_target=any(
                not u.contaminated and self.scenario.is_target_unit(u.id) for u in decision.allowed_units
            )
        )
        new_violations = self.phases.violations[n_violations:]

        history = self.history + [("interviewer", heard)]
        attempts, response, fallback = self._realize(decision, history, known=before.revealed)
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
            )
        )
        self.log.phase_violations = list(self.phases.violations)
        return TurnResult(
            response=response,
            classification=classification,
            decision=decision,
            state=after,
            phase=phase,
            violations=new_violations,
            fallback_used=fallback,
        )

    @property
    def phase(self) -> Phase:
        return self.phases.phase

    def _realize(self, decision: Decision, history, known: list[str]) -> tuple[list[AttemptRecord], str, bool]:
        attempts: list[AttemptRecord] = []
        for attempt in range(MAX_REALIZATION_ATTEMPTS):
            r = self.realizer.realize(decision, self.scenario.child_profile, list(history), attempt=attempt)
            verdict = self.output_filter.check(r.text, decision, known_unit_ids=known)
            attempts.append(
                AttemptRecord(
                    text=r.text,
                    prompt=r.prompt,
                    ok=verdict.ok,
                    forbidden_terms=verdict.forbidden_terms,
                    leaked_units=verdict.leaked_units,
                    missing_units=verdict.missing_units,
                    empty=verdict.empty,
                    meta=r.meta,
                )
            )
            if verdict.ok:
                return attempts, r.text, False
        # Fallback: authored unit values / canned response — safe by construction.
        fallback = TemplateRealizer().realize(decision, self.scenario.child_profile, list(history)).text
        return attempts, fallback, True

    def end(self) -> SessionLog:
        if not self._ended:
            self._ended = True
            self.log.phase_violations = list(self.phases.finish())
            self.log.ended_at = _now()
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
    return f"{name}({model})" if model else name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
