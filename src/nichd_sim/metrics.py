"""Objective metrics, computed from the session log and the scenario — no LLM involved."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from nichd_sim.classification import QuestionType
from nichd_sim.phases import Phase
from nichd_sim.scenario import Centrality, Scenario

if TYPE_CHECKING:
    from nichd_sim.session import SessionLog

OPEN_TYPES = {QuestionType.INVITATION, QuestionType.CUED_INVITATION}
QUESTION_TYPES = OPEN_TYPES | {
    QuestionType.DIRECTIVE,
    QuestionType.OPTION_POSING,
    QuestionType.SUGGESTIVE,
    QuestionType.COMPOUND,
}
"""Facilitators, ground rules, support and `other` are not questions: excluded from the denominator."""


class OpenQuestionRatio(BaseModel):
    open_questions: int
    questions: int
    ratio: float | None
    """None when no question was asked in the substantive phase."""
    by_type: dict[str, int]


class ElicitedUnit(BaseModel):
    id: str
    value: str
    centrality: Centrality
    turn: int
    question_type: QuestionType
    """Type of the question that first elicited the unit (effective type for compound questions)."""


class AccurateInfoRecall(BaseModel):
    revealed: int
    total: int
    ratio: float
    central_revealed: int
    central_total: int
    peripheral_revealed: int
    peripheral_total: int
    elicited: list[ElicitedUnit]
    by_question_type: dict[str, int]


class ContaminationEntry(BaseModel):
    id: str
    value: str
    source_turn: int
    source_type: QuestionType
    source_utterance: str
    integrated: bool


class ContaminationScore(BaseModel):
    contaminated: int
    true_revealed: int
    score: float
    """contaminated / (true revealed + contaminated); 0 when nothing was said."""
    entries: list[ContaminationEntry]


class Metrics(BaseModel):
    open_question_ratio: OpenQuestionRatio
    accurate_info_recall: AccurateInfoRecall
    contamination_score: ContaminationScore


def compute_metrics(log: SessionLog, scenario: Scenario) -> Metrics:
    return Metrics(
        open_question_ratio=_open_ratio(log),
        accurate_info_recall=_recall(log, scenario),
        contamination_score=_contamination(log, scenario),
    )


def _open_ratio(log: SessionLog) -> OpenQuestionRatio:
    by_type: dict[str, int] = {}
    for t in log.turns:
        if t.asked_in != Phase.SUBSTANTIVE or t.classification.type not in QUESTION_TYPES:
            continue
        by_type[t.classification.type.value] = by_type.get(t.classification.type.value, 0) + 1
    questions = sum(by_type.values())
    open_q = sum(n for k, n in by_type.items() if QuestionType(k) in OPEN_TYPES)
    return OpenQuestionRatio(
        open_questions=open_q, questions=questions, ratio=open_q / questions if questions else None, by_type=by_type
    )


def _recall(log: SessionLog, scenario: Scenario) -> AccurateInfoRecall:
    target = [u for _, u in scenario.target_units()]
    elicited: dict[str, ElicitedUnit] = {}
    for t in log.turns:
        qtype = t.decision.effective_type or t.classification.type
        for au in t.decision.allowed_units:
            if au.contaminated or au.id in elicited or not scenario.is_target_unit(au.id):
                continue
            unit = scenario.unit(au.id)
            elicited[au.id] = ElicitedUnit(
                id=unit.id, value=unit.value, centrality=unit.centrality, turn=t.index, question_type=qtype
            )
    items = list(elicited.values())
    central_total = sum(u.centrality == Centrality.CENTRAL for u in target)
    central = sum(e.centrality == Centrality.CENTRAL for e in items)
    by_type: dict[str, int] = {}
    for e in items:
        by_type[e.question_type.value] = by_type.get(e.question_type.value, 0) + 1
    return AccurateInfoRecall(
        revealed=len(items),
        total=len(target),
        ratio=len(items) / len(target) if target else 0.0,
        central_revealed=central,
        central_total=central_total,
        peripheral_revealed=len(items) - central,
        peripheral_total=len(target) - central_total,
        elicited=items,
        by_question_type=by_type,
    )


def _contamination(log: SessionLog, scenario: Scenario) -> ContaminationScore:
    final = log.turns[-1].state_after if log.turns else None
    utterances = {t.index: (t.classification.clean_text or t.utterance) for t in log.turns}
    entries = [
        ContaminationEntry(
            id=cu.id,
            value=cu.value,
            source_turn=cu.source_turn,
            source_type=cu.source_type,
            source_utterance=utterances.get(cu.source_turn, ""),
            integrated=cu.integrated,
        )
        for cu in (final.contaminated if final else [])
    ]
    true_revealed = sum(scenario.is_target_unit(u) for u in (final.revealed if final else []))
    said = true_revealed + len(entries)
    return ContaminationScore(
        contaminated=len(entries),
        true_revealed=true_revealed,
        score=len(entries) / said if said else 0.0,
        entries=entries,
    )
