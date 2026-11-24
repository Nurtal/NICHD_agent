"""Session replay (from a JSON log, without any LLM call) and coder export."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from nichd_sim.classification import Classification, ClassificationContext
from nichd_sim.parameters import Parameters
from nichd_sim.realization import Realization
from nichd_sim.scenario import Scenario, ScenarioError, load_scenario
from pydantic import BaseModel, ValidationError

from nichd_sim.session import LOG_FORMAT, WAIT, Session, SessionLog, apply_profile


class ReplayError(RuntimeError):
    pass


def load_log(path: str | Path) -> SessionLog:
    path = Path(path)
    try:
        return SessionLog.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ReplayError(f"journal introuvable : {path}") from e
    except ValidationError as e:
        raise ReplayError(
            f"{path.name} : journal illisible ou d'un format antérieur (format attendu : {LOG_FORMAT}) — "
            f"{e.error_count()} erreur(s) de validation"
        ) from e


def find_scenario(log: SessionLog, directory: str | Path = "scenarios") -> Scenario:
    """Find the scenario sheet matching the log's id and version."""
    for path in sorted(Path(directory).glob("*.yaml")):
        try:
            sc = load_scenario(path)
        except ScenarioError:
            continue
        if sc.id == log.scenario_id:
            if sc.version != log.scenario_version:
                raise ReplayError(
                    f"{path.name} est en version {sc.version}, le journal a été produit avec {log.scenario_version}"
                )
            return sc
    raise ReplayError(f"aucun scénario {log.scenario_id!r} dans {directory}")


class _LoggedClassifier:
    """Returns the logged classifications, in order."""

    def __init__(self, log: SessionLog):
        self._items = [t.classification for t in log.turns if t.kind != WAIT]  # waits are not classified

    def classify(self, utterance: str, context: ClassificationContext) -> Classification:
        return self._items.pop(0)


class _LoggedRealizer:
    """Returns the logged realization attempts, in order."""

    def __init__(self, log: SessionLog):
        self._turns = [list(t.attempts) for t in log.turns]
        self._current: list = []

    def realize(self, decision, profile, history, attempt=0) -> Realization:
        if attempt == 0:
            self._current = self._turns.pop(0)
        if attempt >= len(self._current):
            raise ReplayError("le rejeu demande plus de tentatives de réalisation que le journal n'en contient")
        a = self._current[attempt]
        return Realization(text=a.text, prompt=a.prompt, meta=a.meta)


@dataclass
class ReplayReport:
    turns: int
    mismatches: list[str] = field(default_factory=list)
    replayed: SessionLog | None = None

    @property
    def identical(self) -> bool:
        return not self.mismatches


def replay(log: SessionLog, scenario: Scenario) -> ReplayReport:
    """Re-run a session from its log and check every decision, response and phase matches."""
    scenario = apply_profile(scenario, log.profile)
    params = Parameters.for_log(scenario.child_profile.age_band, log.parameters)
    session = Session(scenario, _LoggedClassifier(log), _LoggedRealizer(log), seed=log.seed, params=params,
                      rules=log.rules)
    report = ReplayReport(turns=len(log.turns))
    for original in log.turns:
        try:
            if original.kind == WAIT:
                session.wait(timing=original.timing)
            else:
                session.turn(original.utterance, timing=original.timing)
        except ReplayError as e:
            report.mismatches.append(f"tour {original.index} : {e}")
            break
        new = session.log.turns[-1]
        for name in ("decision", "phase", "response", "fallback_used", "state_after"):
            if not _same(getattr(new, name), getattr(original, name), name, log.log_format):
                report.mismatches.append(f"tour {original.index} : {name} diffère")
    replayed = session.end()
    if replayed.phase_violations != log.phase_violations:
        report.mismatches.append("écarts au protocole différents")
    report.replayed = replayed
    return report


_ADDED_IN: dict[int, dict[str, set[str]]] = {
    3: {"decision": {"delivery", "demeanor"}, "state_after": {"arousal", "arousal_baseline"}},
    4: {"state_after": {"last_act", "last_target", "closed_asked", "last_key", "supports_given"}},
    5: {"state_after": {"promised"}},
    6: {"state_after": {"expressivity"}},
}
"""Per log format, the fields it added or computes differently (format 3: the delivery depends on
arousal; format 4: the engine remembers the previous turn and the closed questions asked; format 5: the
promise to tell the truth). They are
not compared for older logs. Decisions themselves must still match."""


def _legacy_exclude(name: str, log_format: int) -> set[str]:
    return set().union(*(fields.get(name, set()) for fmt, fields in _ADDED_IN.items() if fmt > log_format))


def _same(new, original, name: str, log_format: int) -> bool:
    """Equality; for older logs, ignore what later formats added (new fields at their default too)."""
    if log_format >= LOG_FORMAT or not isinstance(new, BaseModel):
        return new == original
    exclude = _legacy_exclude(name, log_format)
    return new.model_dump(exclude=exclude, exclude_defaults=True) == original.model_dump(
        exclude=exclude, exclude_defaults=True
    )


CODER_COLUMNS = ["tour", "locuteur", "enonce", "code"]


def export_for_coders(log: SessionLog, path: str | Path) -> Path:
    """Blank transcript for human coders: no automatic classification, empty code column.

    Semicolon-separated, UTF-8 with BOM (opens directly in French spreadsheet software)."""
    path = Path(path)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(CODER_COLUMNS)
        for t in log.turns:
            heard = t.classification.clean_text or t.utterance
            w.writerow([t.index, "interviewer", heard, ""])
            w.writerow([t.index, "enfant", t.response, ""])
    return path
