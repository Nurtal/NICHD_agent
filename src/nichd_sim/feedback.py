"""Structured feedback report for the learner."""

from __future__ import annotations

import json
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


class SummaryMatch(BaseModel):
    """How the learner's written summary maps onto what the child said."""

    retained_true: list[str] = []
    """True unit ids the child said and the learner reported."""
    retained_contaminated: list[str] = []
    """Contaminated unit ids (false details) the learner reported as facts."""
    not_said_by_child: list[str] = []
    """Statements of the summary that match nothing the child said."""


class SummaryMatcher(Protocol):
    def match(self, summary: str, said_true: list[tuple[str, str]], said_false: list[tuple[str, str]]) -> SummaryMatch: ...


SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "retained_true": {"type": "array", "items": {"type": "string"}},
        "retained_contaminated": {"type": "array", "items": {"type": "string"}},
        "not_said_by_child": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["retained_true", "retained_contaminated", "not_said_by_child"],
}


class LLMSummaryMatcher:
    """Matches a learner's summary against the child's statements with the local LLM."""

    def __init__(self, client: ChatClient):
        self.client = client

    def match(self, summary, said_true, said_false) -> SummaryMatch:
        catalog = "\n".join(f"- {i} : {v}" for i, v in said_true + said_false) or "- (rien)"
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu compares la synthèse écrite par un enquêteur avec ce qu'un enfant a réellement dit "
                    "pendant une audition. Pour chaque élément de la liste que la synthèse rapporte (même "
                    "reformulé), donne son identifiant : dans `retained_true` si l'identifiant ne commence pas "
                    "par « c », dans `retained_contaminated` s'il commence par « c ». Dans `not_said_by_child`, "
                    "recopie brièvement chaque affirmation de la synthèse qui ne correspond à rien de la liste. "
                    "Réponds uniquement en JSON."
                ),
            },
            {"role": "user", "content": f"Ce que l'enfant a dit :\n{catalog}\n\nSynthèse de l'enquêteur :\n{summary}"},
        ]
        result = self.client.chat(messages, temperature=0, seed=0, think=False, format=SUMMARY_SCHEMA)
        try:
            return SummaryMatch.model_validate(json.loads(result.content))
        except ValueError:
            return SummaryMatch()


class LearnerSummaryResult(BaseModel):
    summary: str
    retained_true: list[str]
    retained_contaminated: list[str]
    not_said_by_child: list[str]
    true_said: int
    recall: float | None
    """Share of the true units the child said that the learner reported."""


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
    learner_summary: LearnerSummaryResult | None = None


def match_summary(summary: str, log: SessionLog, scenario: Scenario, matcher: SummaryMatcher) -> LearnerSummaryResult:
    final = log.turns[-1].state_after if log.turns else None
    said_true = [(u, scenario.unit(u).value) for u in (final.revealed if final else []) if scenario.is_target_unit(u)]
    said_false = [(cu.id, cu.value) for cu in (final.contaminated if final else [])]
    try:
        m = matcher.match(summary, said_true, said_false)
    except LLMError:
        m = SummaryMatch()
    true_ids = {i for i, _ in said_true}
    false_ids = {i for i, _ in said_false}
    retained_true = [i for i in dict.fromkeys(m.retained_true) if i in true_ids]
    retained_false = [i for i in dict.fromkeys(m.retained_contaminated) if i in false_ids]
    return LearnerSummaryResult(
        summary=summary,
        retained_true=retained_true,
        retained_contaminated=retained_false,
        not_said_by_child=[s for s in m.not_said_by_child if s.strip()],
        true_said=len(true_ids),
        recall=len(retained_true) / len(true_ids) if true_ids else None,
    )


def build_feedback(
    log: SessionLog,
    scenario: Scenario,
    rephraser: Rephraser | None = None,
    learner_summary: str | None = None,
    summary_matcher: SummaryMatcher | None = None,
) -> FeedbackReport:
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
        learner_summary=(
            match_summary(learner_summary, log, scenario, summary_matcher)
            if learner_summary and learner_summary.strip() and summary_matcher is not None
            else None
        ),
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
    ls = report.learner_summary
    if ls is not None:
        out.append("")
        out.append(f"Votre synthèse : {_pct(ls.recall)} des faits dits par l'enfant retenus ({len(ls.retained_true)}/{ls.true_said})")
        if ls.retained_contaminated:
            out.append(f"  ⚠ {len(ls.retained_contaminated)} faux détail(s) repris comme des faits : {', '.join(ls.retained_contaminated)}")
        for item in ls.not_said_by_child:
            out.append(f"  ⚠ jamais dit par l'enfant : « {item} »")
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
