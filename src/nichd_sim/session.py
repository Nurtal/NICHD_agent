"""Session facade: the single entry point used by the CLI, the UI and the tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from nichd_sim.classification import Classification, ClassificationContext, Classifier
from nichd_sim.engine import BehaviorEngine, Decision, EngineState
from nichd_sim.parameters import Parameters
from nichd_sim.realization import Realizer
from nichd_sim.scenario import Scenario


class TurnRecord(BaseModel):
    index: int
    utterance: str
    classification: Classification
    state_before: EngineState
    decision: Decision
    state_after: EngineState
    prompt: str | None = None
    response: str


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


class TurnResult(BaseModel):
    """What one turn exposes: the child's response plus trainer-mode details."""

    response: str
    classification: Classification
    decision: Decision
    state: EngineState


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
        log_dir: str | Path | None = None,
    ):
        self.scenario = scenario
        self.classifier = classifier
        self.realizer = realizer
        self.seed = seed
        self.params = params or Parameters.load(scenario.child_profile.age_band, scenario.parameter_overrides)
        self.log_dir = Path(log_dir) if log_dir else None
        self.engine = BehaviorEngine(scenario, self.params, seed)
        self.history: list[tuple[str, str]] = []
        self.log = SessionLog(
            session_id=uuid.uuid4().hex[:12],
            started_at=_now(),
            scenario_id=scenario.id,
            scenario_version=scenario.version,
            seed=seed,
            parameters=self.params.snapshot(),
            components={
                "classifier": type(classifier).__name__,
                "realizer": type(realizer).__name__,
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
        classification = self.classifier.classify(utterance, context)
        before = self.state
        decision = self.engine.decide(classification)
        realization = self.realizer.realize(decision, self.scenario.child_profile, list(self.history))
        after = self.state

        heard = classification.clean_text or utterance
        self.history += [("interviewer", heard), ("child", realization.text)]
        self.log.turns.append(
            TurnRecord(
                index=len(self.log.turns) + 1,
                utterance=utterance,
                classification=classification,
                state_before=before,
                decision=decision,
                state_after=after,
                prompt=realization.prompt,
                response=realization.text,
            )
        )
        return TurnResult(response=realization.text, classification=classification, decision=decision, state=after)

    def end(self) -> SessionLog:
        if not self._ended:
            self._ended = True
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
