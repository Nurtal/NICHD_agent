"""Protocol coaching (ADR 0004, addendum): how the learner is doing, turn by turn.

The performance contract describes the child; this channel describes the interviewer. It is a separate
file (`coaching.json`) for the learner's screen.

What is shown during the interview must not tell the learner anything the child's words do not:
a turn's tag and alerts depend only on what the learner said and on the phase it was said in, and the
live fact counter leaves out what would confirm a suggestion or expose a lie. Everything held back
appears in the debrief, once the interview is over.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from nichd_sim.classification import QuestionType
from nichd_sim.engine import closed_key, is_rejection
from nichd_sim.feedback import PHASE_LABELS, TYPE_LABELS
from nichd_sim.metrics import compute_metrics
from nichd_sim.phases import ORDER, VIOLATION_LABELS, Phase, PhaseViolation, ViolationKind
from nichd_sim.scenario import Centrality

if TYPE_CHECKING:
    from nichd_sim.scenario import Scenario
    from nichd_sim.session import SessionLog, TurnRecord

COACHING_FORMAT = 1


class Level(StrEnum):
    OK = "ok"
    WATCH = "watch"
    ALERT = "alert"


# Proposed scale, to be validated by a NICHD trainer.
TYPE_LEVELS = {
    QuestionType.INVITATION: Level.OK,
    QuestionType.CUED_INVITATION: Level.OK,
    QuestionType.FACILITATOR: Level.OK,
    QuestionType.GROUND_RULE: Level.OK,
    QuestionType.SUPPORT: Level.OK,
    QuestionType.DIRECTIVE: Level.WATCH,
    QuestionType.OPTION_POSING: Level.WATCH,
    QuestionType.COMPOUND: Level.WATCH,
    QuestionType.OTHER: Level.WATCH,
    QuestionType.SUGGESTIVE: Level.ALERT,
}

TYPE_ADVICE = {
    QuestionType.DIRECTIVE: ("Question directive", "À réserver aux détails que les invitations n'ont pas fait émerger."),
    QuestionType.OPTION_POSING: ("Question à choix", "Elle limite la réponse : revenez à une invitation ouverte (« Dis-m'en plus sur… »)."),
    QuestionType.COMPOUND: ("Plusieurs questions à la fois", "Posez une seule question, de préférence ouverte."),
    QuestionType.OTHER: ("Énoncé hors protocole", "Revenez à une invitation ou à un encouragement neutre."),
    QuestionType.SUGGESTIVE: ("Question suggestive", "Elle apporte une information que l'enfant n'a pas donnée. Repartez de ses propres mots."),
}

PHASE_ADVICE = {
    ViolationKind.SKIPPED_PHASE: "Cette étape prépare l'enfant au récit : ne la passez pas.",
    ViolationKind.TRUNCATED_PHASE: "Prenez le temps de cette étape avant de passer à la suivante.",
    ViolationKind.PREMATURE_FOCUSED_QUESTION: "Attendez la transition, puis laissez l'enfant amener les faits.",
}

REJECTION_ADVICE = (
    "« Je sais pas » ou « non » repris",
    "Acceptez la réponse et passez à autre chose, ou revenez à une invitation : reposer la question pousse "
    "l'enfant à répondre pour vous satisfaire.",
)
REPETITION_ADVICE = (
    "Question déjà posée",
    "Répétée, une question fait croire à l'enfant que sa première réponse était fausse : il risque d'en changer "
    "ou d'inventer.",
)
KNOWLEDGE_ADVICE = (
    "« Est-ce que tu sais / te souviens… ? »",
    "L'enfant peut répondre « oui » sans rien dire de plus : demandez directement (« Qu'est-ce que… ? »), ou "
    "mieux, invitez-le à raconter.",
)
"""Interaction alerts (docs/plans/adaptations-litterature.md, lots 1 and 2). They depend only on the learner's
questions and on what the child visibly answered, never on whether that answer was true."""

LIVE_VIOLATIONS = set(PHASE_ADVICE)
"""Forced disclosure stays out of the live alerts: announcing it would confirm the suggestion."""


class Tag(BaseModel):
    type: QuestionType
    label: str
    level: Level


class Alert(BaseModel):
    kind: str
    level: Level
    message: str
    hint: str


class TurnCoaching(BaseModel):
    turn: int
    phase: Phase
    """Phase in which the learner spoke."""
    phase_label: str
    tag: Tag
    alerts: list[Alert] = []
    facts_found: int | None
    """Live counter after this turn's reply. None when it is hidden until the debrief."""


class PhaseItem(BaseModel):
    id: Phase
    label: str


class Debrief(BaseModel):
    facts_found: int
    facts_total: int
    central_found: int
    central_total: int
    open_questions: int
    questions: int
    open_ratio: float | None
    false_details: int
    issues: list[str]
    """Protocol deviations that were not shown during the interview."""
    contradictions: list[str] = []
    """Truths that slipped out against an earlier lie: never shown live, it would expose the lie."""


class SessionCoaching(BaseModel):
    format: int = COACHING_FORMAT
    session_id: str
    phases: list[PhaseItem]
    facts_total: int
    facts_hidden: bool
    """True when the scenario has hidden facts: the live counter would expose the lies."""
    turns: list[TurnCoaching]
    debrief: Debrief


def _is_live(v: PhaseViolation, asked_in: Phase) -> bool:
    """Shown during the interview? A violation raised by the child's disclosure (at or after the phase
    the learner spoke in) is not: it would tell that what the child just said was true."""
    if v.kind not in LIVE_VIOLATIONS:
        return False
    return v.kind == ViolationKind.PREMATURE_FOCUSED_QUESTION or ORDER.index(v.phase) < ORDER.index(asked_in)


def _violation_text(v: PhaseViolation) -> str:
    label = VIOLATION_LABELS[v.kind].capitalize()
    return label if v.kind == ViolationKind.MISSING_CLOSURE else f"{label} ({PHASE_LABELS[v.phase]})"


def _tag(t: TurnRecord, premature: bool) -> Tag:
    c = t.classification
    level = TYPE_LEVELS[c.type]
    if c.type == QuestionType.COMPOUND and c.inner_type == QuestionType.SUGGESTIVE:
        level = Level.ALERT
    if premature:
        level = Level.ALERT
    return Tag(type=c.type, label=TYPE_LABELS[c.type], level=level)


def _effective(t: TurnRecord) -> QuestionType:
    c = t.classification
    return (c.inner_type or QuestionType.DIRECTIVE) if c.type == QuestionType.COMPOUND else c.type


def _key(t: TurnRecord) -> str | None:
    return closed_key(t.classification, _effective(t), t.classification.clean_text or t.utterance)


def _interaction_alerts(t: TurnRecord, prev: TurnRecord | None, asked: dict[str, int]) -> list[Alert]:
    alerts = []
    if t.classification.knowledge_question:
        alerts.append(Alert(kind="knowledge_question", level=Level.WATCH, message=KNOWLEDGE_ADVICE[0], hint=KNOWLEDGE_ADVICE[1]))
    return alerts + _repeat_alerts(t, prev, asked)


def _repeat_alerts(t: TurnRecord, prev: TurnRecord | None, asked: dict[str, int]) -> list[Alert]:
    key = _key(t)
    if key is None:
        return []
    level = Level.ALERT if _effective(t) == QuestionType.SUGGESTIVE else Level.WATCH
    if prev is not None and is_rejection(prev.decision.speech_act, _key(prev), key):
        return [Alert(kind="rejected_refusal", level=level, message=REJECTION_ADVICE[0], hint=REJECTION_ADVICE[1])]
    if asked.get(key, 0):
        return [Alert(kind="repeated_question", level=level, message=REPETITION_ADVICE[0], hint=REPETITION_ADVICE[1])]
    return []


def _alerts(t: TurnRecord, live: list[PhaseViolation], tag: Tag, interaction: list[Alert]) -> list[Alert]:
    alerts = []
    advice = TYPE_ADVICE.get(t.classification.type)
    if advice is not None:
        alerts.append(Alert(kind=t.classification.type.value, level=tag.level, message=advice[0], hint=advice[1]))
    alerts += interaction
    for v in live:
        level = Level.ALERT if v.kind == ViolationKind.PREMATURE_FOCUSED_QUESTION else Level.WATCH
        alerts.append(Alert(kind=v.kind.value, level=level, message=_violation_text(v), hint=PHASE_ADVICE[v.kind]))
    return alerts


def _contradictions(metrics) -> list[str]:
    if metrics.deception is None:
        return []
    return [
        f"Tour {e.leaked_turn} : la vérité lui échappe, alors qu'au tour {e.turn} l'enfant avait dit « {e.value} »."
        for e in metrics.deception.lies if e.leaked_turn is not None
    ]


def build_coaching(log: SessionLog, scenario: Scenario) -> SessionCoaching:
    metrics = compute_metrics(log, scenario)
    recall = metrics.accurate_info_recall
    hidden = scenario.deception is not None
    lucky_turns = {t.index for t in log.turns if t.decision.lucky_suggestion}
    countable = [e.turn for e in recall.elicited if e.turn not in lucky_turns]

    shown: set[int] = set()
    turns = []
    asked_in = {t.index: t.asked_in for t in log.turns}
    asked: dict[str, int] = {}
    prev = None
    for t in log.turns:
        interaction = _interaction_alerts(t, prev, asked)
        if (key := _key(t)) is not None:
            asked[key] = asked.get(key, 0) + 1
        prev = t
        live = []
        for i, v in enumerate(log.phase_violations):
            if v.turn == t.index and _is_live(v, asked_in[t.index]):
                live.append(v)
                shown.add(i)
        premature = any(v.kind == ViolationKind.PREMATURE_FOCUSED_QUESTION for v in live)
        tag = _tag(t, premature)
        turns.append(TurnCoaching(
            turn=t.index, phase=t.asked_in, phase_label=PHASE_LABELS[t.asked_in], tag=tag,
            alerts=_alerts(t, live, tag, interaction),
            facts_found=None if hidden else sum(turn <= t.index for turn in countable),
        ))

    oq = metrics.open_question_ratio
    return SessionCoaching(
        session_id=log.session_id,
        phases=[PhaseItem(id=p, label=PHASE_LABELS[p]) for p in ORDER],
        facts_total=recall.total,
        facts_hidden=hidden,
        turns=turns,
        debrief=Debrief(
            facts_found=recall.revealed, facts_total=recall.total,
            central_found=sum(e.centrality == Centrality.CENTRAL for e in recall.elicited),
            central_total=recall.central_total,
            open_questions=oq.open_questions, questions=oq.questions, open_ratio=oq.ratio,
            false_details=metrics.contamination_score.contaminated,
            issues=[_violation_text(v) for i, v in enumerate(log.phase_violations) if i not in shown],
            contradictions=_contradictions(metrics),
        ),
    )


def write_coaching(coaching: SessionCoaching, out_dir: str | Path) -> Path:
    path = Path(out_dir) / "coaching.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(coaching.model_dump_json(indent=2), encoding="utf-8")
    return path
