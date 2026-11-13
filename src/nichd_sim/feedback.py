"""Structured feedback report for the learner."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel

from nichd_sim.classification import QuestionType
from nichd_sim.llm import ChatClient, LLMError
from nichd_sim.metrics import Metrics, compute_metrics
from nichd_sim.phases import VIOLATION_LABELS, Phase, PhaseViolation
from nichd_sim.scenario import Scenario

if TYPE_CHECKING:
    from nichd_sim.session import SessionLog

TO_REPHRASE = {QuestionType.DIRECTIVE, QuestionType.OPTION_POSING, QuestionType.SUGGESTIVE, QuestionType.COMPOUND}

TYPE_LABELS = {
    QuestionType.INVITATION: "invitation",
    QuestionType.CUED_INVITATION: "invitation indicée",
    QuestionType.DIRECTIVE: "question directive",
    QuestionType.OPTION_POSING: "question à choix",
    QuestionType.SUGGESTIVE: "question suggestive",
    QuestionType.FACILITATOR: "facilitateur",
    QuestionType.GROUND_RULE: "règle de base",
    QuestionType.SUPPORT: "soutien",
    QuestionType.COMPOUND: "question composée",
    QuestionType.OTHER: "hors protocole",
}

PHASE_LABELS = {
    Phase.RAPPORT: "rapport",
    Phase.GROUND_RULES: "règles de base",
    Phase.NARRATIVE_PRACTICE: "pratique narrative",
    Phase.TRANSITION: "transition",
    Phase.SUBSTANTIVE: "phase substantive",
    Phase.CLOSURE: "clôture",
}


class Rephraser(Protocol):
    def rephrase(self, question: str, child_said: list[str]) -> str: ...


class LLMRephraser:
    """Proposes an open-ended NICHD reformulation of a closed/suggestive question."""

    def __init__(self, client: ChatClient, temperature: float = 0.3):
        self.client = client
        self.temperature = temperature

    def rephrase(self, question: str, child_said: list[str]) -> str:
        said = "\n".join(f"- {t}" for t in child_said[-6:]) or "- (rien)"
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es formateur au protocole d'audition NICHD. On te donne une question fermée, directive "
                    "ou suggestive posée à un enfant. Propose UNE reformulation en invitation ouverte "
                    "(« Dis-moi tout sur… », « Raconte-moi… », « Tu as parlé de…, dis-m'en plus »). "
                    "Ne reprends que des éléments que l'enfant a déjà dits lui-même ; n'introduis aucune "
                    "information nouvelle. Réponds uniquement par la question reformulée."
                ),
            },
            {"role": "user", "content": f"Ce que l'enfant a déjà dit :\n{said}\n\nQuestion posée : {question}"},
        ]
        result = self.client.chat(messages, temperature=self.temperature, seed=0, think=False)
        return " ".join(result.content.split())


class Rephrasing(BaseModel):
    turn: int
    question: str
    question_type: QuestionType
    suggestion: str
    generated: bool = True
    """Always True: produced by a language model, to be read critically."""


class TranscriptLine(BaseModel):
    turn: int
    phase: Phase
    question_type: QuestionType
    interviewer: str
    child: str
    flags: list[str] = []


class FlaggedTurn(BaseModel):
    turn: int
    utterance: str
    note: str


class FeedbackReport(BaseModel):
    metrics: Metrics
    phase_violations: list[PhaseViolation]
    phases_visited: list[Phase]
    transcript: list[TranscriptLine]
    rephrasings: list[Rephrasing]
    lucky_suggestions: list[FlaggedTurn]
    """Closed/suggestive questions that happened to be true: still technique faults."""
    off_protocol: list[FlaggedTurn]
    disclosed: bool


def build_feedback(log: SessionLog, scenario: Scenario, rephraser: Rephraser | None = None) -> FeedbackReport:
    transcript, rephrasings, lucky, off = [], [], [], []
    child_said: list[str] = []
    for t in log.turns:
        heard = t.classification.clean_text or t.utterance
        qtype = t.classification.type
        flags = []
        if t.decision.lucky_suggestion:
            flags.append("suggestion tombée juste")
            lucky.append(FlaggedTurn(turn=t.index, utterance=heard, note="la réponse était vraie par hasard : faute de technique"))
        if t.decision.new_contamination:
            flags.append(f"contamination {t.decision.new_contamination}")
        if t.decision.forced_disclosure:
            flags.append("dévoilement forcé")
        if qtype == QuestionType.OTHER:
            off.append(FlaggedTurn(turn=t.index, utterance=heard, note="énoncé hors protocole"))
        if qtype in TO_REPHRASE and rephraser is not None:
            try:
                suggestion = rephraser.rephrase(heard, child_said)
            except LLMError:
                suggestion = ""
            if suggestion:
                rephrasings.append(Rephrasing(turn=t.index, question=heard, question_type=qtype, suggestion=suggestion))
        transcript.append(
            TranscriptLine(turn=t.index, phase=t.asked_in, question_type=qtype, interviewer=heard, child=t.response, flags=flags)
        )
        child_said.append(t.response)
    visited: list[Phase] = []
    for t in log.turns:
        for p in (t.asked_in, t.phase):
            if p not in visited:
                visited.append(p)
    return FeedbackReport(
        metrics=compute_metrics(log, scenario),
        phase_violations=list(log.phase_violations),
        phases_visited=visited,
        transcript=transcript,
        rephrasings=rephrasings,
        lucky_suggestions=lucky,
        off_protocol=off,
        disclosed=bool(log.turns and log.turns[-1].state_after.disclosed),
    )


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.0f} %"


def render_text(report: FeedbackReport) -> str:
    m = report.metrics
    oq, rc, ct = m.open_question_ratio, m.accurate_info_recall, m.contamination_score
    out = ["", "══════════ Retour sur l'entretien ══════════", ""]
    out.append(f"Questions ouvertes (phase substantive) : {_pct(oq.ratio)}  ({oq.open_questions}/{oq.questions})")
    if oq.by_type:
        out.append("  " + ", ".join(f"{TYPE_LABELS[QuestionType(k)]} : {n}" for k, n in sorted(oq.by_type.items())))
    out.append(
        f"Informations exactes recueillies : {_pct(rc.ratio)}  ({rc.revealed}/{rc.total} — "
        f"centrales {rc.central_revealed}/{rc.central_total}, périphériques {rc.peripheral_revealed}/{rc.peripheral_total})"
    )
    if rc.by_question_type:
        out.append("  obtenues par : " + ", ".join(f"{TYPE_LABELS[QuestionType(k)]} {n}" for k, n in rc.by_question_type.items()))
    out.append(f"Score de contamination : {_pct(ct.score)}  ({ct.contaminated} faux détail(s))")
    for e in ct.entries:
        out.append(f"  - « {e.value} » — introduit au tour {e.source_turn} ({TYPE_LABELS[e.source_type]}) : « {e.source_utterance} »")
    if not report.disclosed:
        out.append("L'enfant n'a pas dévoilé l'événement : c'est un résultat possible et légitime.")
    out.append("")
    out.append("Phases : " + " → ".join(PHASE_LABELS[p] for p in report.phases_visited))
    if report.phase_violations:
        out.append("Écarts au protocole :")
        for v in report.phase_violations:
            where = f"tour {v.turn}" if v.turn else "fin"
            out.append(f"  - {VIOLATION_LABELS[v.kind]} ({PHASE_LABELS[v.phase]}, {where}){' — ' + v.detail if v.detail else ''}")
    for title, items in (("Suggestions tombées juste (fautes de technique)", report.lucky_suggestions), ("Énoncés hors protocole", report.off_protocol)):
        if items:
            out.append(f"{title} :")
            out += [f"  - tour {f.turn} : « {f.utterance} »" for f in items]
    if report.rephrasings:
        out.append("")
        out.append("Reformulations proposées (générées automatiquement, à lire avec esprit critique) :")
        for r in report.rephrasings:
            out.append(f"  - tour {r.turn} ({TYPE_LABELS[r.question_type]}) « {r.question} »")
            out.append(f"      → « {r.suggestion} »")
    out.append("")
    out.append("Transcription annotée :")
    for line in report.transcript:
        flags = f"  [{', '.join(line.flags)}]" if line.flags else ""
        out.append(f"  {line.turn:>2}. ({TYPE_LABELS[line.question_type]}) {line.interviewer}{flags}")
        out.append(f"      ↳ {line.child}")
    return "\n".join(out)
