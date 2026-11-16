"""Objective metrics, computed from the session log and the scenario — no LLM involved."""

from __future__ import annotations

import statistics
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


class LieEntry(BaseModel):
    id: str
    kind: str
    protected: str
    """Protected (true) unit the lie was about."""
    value: str
    turn: int
    question_type: QuestionType
    utterance: str
    """The interviewer's utterance that drew the lie."""
    times: int
    retracted_turn: int | None


class DeceptionSummary(BaseModel):
    """What the child hid, how, and what the interviewer finally obtained (ADR 0002)."""

    protected_total: int
    protected_obtained: list[ElicitedUnit]
    """Protected facts finally told truthfully, with the question type that obtained them."""
    lies: list[LieEntry]
    """Active lies (denials, feigned ignorance, cover stories, minimizations)."""
    omissions: list[str]
    """Protected units deliberately left out of a narrative at least once."""
    retracted: int
    standing: int
    """Lies never taken back by the end of the interview."""
    lies_by_question_type: dict[str, int]


HESITATION_MS = 1500
"""A child reply whose initial silence lasts at least this long is a hesitation to respect."""


class TurnTakingSummary(BaseModel):
    """Voice sessions: did the learner leave the child time to answer?"""

    timed_turns: int
    median_wait_ms: int | None
    """Median wait after the child's reply, over the turns that did not interrupt."""
    interruptions: dict[str, int]
    """Interruptions by moment: onset (before the child started), pause, speech."""
    hesitations: int
    """Child replies with an initial silence ≥ HESITATION_MS, followed by a learner turn."""
    hesitations_respected: int
    """…that the learner let the child get through (no interruption during the onset)."""
    units_cut: list[str]
    """Units the child did not get to say because of an interruption."""


class Metrics(BaseModel):
    open_question_ratio: OpenQuestionRatio
    accurate_info_recall: AccurateInfoRecall
    contamination_score: ContaminationScore
    deception: DeceptionSummary | None = None
    """Only for scenarios with a `deception` block."""
    turn_taking: TurnTakingSummary | None = None
    """Only for voice sessions (turns with timing)."""


def compute_metrics(log: SessionLog, scenario: Scenario) -> Metrics:
    recall = _recall(log, scenario)
    return Metrics(
        open_question_ratio=_open_ratio(log),
        accurate_info_recall=recall,
        contamination_score=_contamination(log, scenario),
        deception=_deception(log, scenario, recall) if scenario.deception is not None else None,
        turn_taking=_turn_taking(log),
    )


def _turn_taking(log: SessionLog) -> TurnTakingSummary | None:
    timed = [(i, t) for i, t in enumerate(log.turns) if t.timing is not None]
    if not timed:
        return None
    waits, kinds, hesitations, respected = [], {}, 0, 0
    for i, t in timed:
        barge = t.timing.barge_in
        if barge is None:
            waits.append(t.timing.wait_ms)
        else:
            kinds[barge.during] = kinds.get(barge.during, 0) + 1
        prev = log.turns[i - 1].decision.delivery if i > 0 else None
        if prev is not None and prev.onset_ms >= HESITATION_MS:
            hesitations += 1
            respected += barge is None or barge.during != "onset"
    return TurnTakingSummary(
        timed_turns=len(timed),
        median_wait_ms=int(statistics.median(waits)) if waits else None,
        interruptions=kinds,
        hesitations=hesitations,
        hesitations_respected=respected,
        units_cut=[u for t in log.turns for u in t.unheard_units],
    )


def _deception(log: SessionLog, scenario: Scenario, recall: AccurateInfoRecall) -> DeceptionSummary:
    final = log.turns[-1].state_after if log.turns else None
    records = final.lies if final else []
    utterances = {t.index: (t.classification.clean_text or t.utterance) for t in log.turns}
    lies = [
        LieEntry(
            id=lr.id, kind=str(lr.kind), protected=lr.protected, value=lr.value, turn=lr.turn,
            question_type=lr.question_type, utterance=utterances.get(lr.turn, ""), times=lr.times,
            retracted_turn=lr.retracted_turn,
        )
        for lr in records
        if lr.kind != "omission"
    ]
    by_type: dict[str, int] = {}
    for e in lies:
        by_type[e.question_type.value] = by_type.get(e.question_type.value, 0) + 1
    protected = set(scenario.deception.protected)
    return DeceptionSummary(
        protected_total=len(protected),
        protected_obtained=[e for e in recall.elicited if e.id in protected],
        lies=lies,
        omissions=sorted({lr.protected for lr in records if lr.kind == "omission"}),
        retracted=sum(e.retracted_turn is not None for e in lies),
        standing=sum(e.retracted_turn is None for e in lies),
        lies_by_question_type=by_type,
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
            if au.contaminated or au.id in elicited or au.id in t.unheard_units or not scenario.is_target_unit(au.id):
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
