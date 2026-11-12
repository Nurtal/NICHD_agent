"""Streamlit interface: interview, trainer mode and feedback screen.

All behaviour goes through the public Session API; this module only displays.
Run with:  uv run nichd-sim ui   (or: uv run streamlit run src/nichd_sim/ui/app.py)
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from nichd_sim.classifiers.llm import LLMClassifier
from nichd_sim.classifiers.manual import HELP, ManualClassificationError, ManualClassifier
from nichd_sim.evaluation import load_scenarios
from nichd_sim.feedback import PHASE_LABELS, TYPE_LABELS, LLMRephraser, LLMSummaryMatcher
from nichd_sim.llm import DEFAULT_MODEL, DEFAULT_URL, LLMError, OllamaClient
from nichd_sim.phases import ORDER as PHASE_ORDER
from nichd_sim.phases import VIOLATION_LABELS
from nichd_sim.realization import LLMRealizer, TemplateRealizer
from nichd_sim.session import Session

SCENARIOS_DIR = Path(os.environ.get("NICHD_SCENARIOS", Path(__file__).resolve().parents[3] / "scenarios"))
LOG_DIR = os.environ.get("NICHD_LOG_DIR", "sessions")
OFFLINE = os.environ.get("NICHD_OFFLINE") == "1"  # template voice + manual classification, no LLM (demo without GPU, tests)

TYPE_COLORS = {
    "invitation": "#2e7d32",
    "cued_invitation": "#43a047",
    "facilitator": "#7cb342",
    "directive": "#f9a825",
    "option_posing": "#ef6c00",
    "suggestive": "#c62828",
    "compound": "#d84315",
    "ground_rule": "#1565c0",
    "support": "#5e35b1",
    "other": "#757575",
}

st.set_page_config(page_title="Simulateur NICHD", page_icon="🗣️", layout="wide")


@st.cache_resource
def scenarios():
    return load_scenarios(SCENARIOS_DIR)


def chip(text: str, color: str) -> str:
    return (
        f"<span style='background:{color};color:white;border-radius:0.6em;padding:0.1em 0.6em;"
        f"font-size:0.8em;white-space:nowrap'>{text}</span>"
    )


def new_session(scenario, seed: int, offline: bool) -> Session:
    if offline:
        classifier, realizer, rephraser, matcher = ManualClassifier(), TemplateRealizer(), None, None
    else:
        client = OllamaClient(DEFAULT_MODEL, DEFAULT_URL)
        classifier, realizer = LLMClassifier(client), LLMRealizer(client, seed=seed)
        rephraser, matcher = LLMRephraser(client), LLMSummaryMatcher(client)
    return Session(
        scenario, classifier, realizer, seed=seed, rephraser=rephraser, summary_matcher=matcher, log_dir=LOG_DIR
    )


def reset():
    for key in ("session", "turns", "ending", "feedback"):
        st.session_state.pop(key, None)


# -- sidebar ---------------------------------------------------------------------

all_scenarios = scenarios()
with st.sidebar:
    st.title("Simulateur NICHD")
    ids = list(all_scenarios)
    chosen = st.selectbox(
        "Scénario", ids, format_func=lambda i: all_scenarios[i].title, key="scenario_id", on_change=reset
    )
    scenario = all_scenarios[chosen]
    profile = scenario.child_profile
    st.caption(f"{profile.name}, {profile.age} ans")
    st.info(scenario.intake_context.strip())
    if scenario.status == "draft":
        st.caption("Scénario en attente de validation par un formateur NICHD.")
    seed = st.number_input("Graine (reproductibilité)", min_value=0, value=0, step=1, key="seed")
    offline = st.toggle("Mode hors ligne (sans LLM)", value=OFFLINE, key="offline",
                        help="Voix gabarit et classification manuelle par préfixes.")
    trainer = st.toggle("Mode formateur", value=False, key="trainer")
    if st.button("Nouvel entretien", type="primary", use_container_width=True):
        reset()
        st.session_state.session = new_session(scenario, int(seed), offline)
        st.session_state.turns = []
        st.rerun()
    if "session" in st.session_state and "feedback" not in st.session_state:
        if st.button("Terminer l'entretien", use_container_width=True):
            st.session_state.ending = True
            st.rerun()

session: Session | None = st.session_state.get("session")

if session is None:
    st.header("Entraînement à l'audition d'enfant — protocole NICHD")
    st.write(
        "Choisissez un scénario puis cliquez sur **Nouvel entretien**. Menez l'audition comme en situation "
        "réelle : rapport, règles de base, pratique narrative, transition, phase substantive, clôture. "
        "Le retour s'affiche quand vous terminez l'entretien."
    )
    st.stop()


# -- feedback screen ---------------------------------------------------------------


def show_feedback(fb):
    st.header("Retour sur l'entretien")
    m = fb.metrics
    oq, rc, ct = m.open_question_ratio, m.accurate_info_recall, m.contamination_score
    c1, c2, c3 = st.columns(3)
    c1.metric("Questions ouvertes (phase substantive)", "—" if oq.ratio is None else f"{oq.ratio:.0%}",
              help=f"{oq.open_questions} sur {oq.questions} questions")
    c2.metric("Informations exactes recueillies", f"{rc.ratio:.0%}",
              help=f"centrales {rc.central_revealed}/{rc.central_total}, périphériques {rc.peripheral_revealed}/{rc.peripheral_total}")
    c3.metric("Score de contamination", f"{ct.score:.0%}", help=f"{ct.contaminated} faux détail(s)")
    if not fb.disclosed:
        st.info("L'enfant n'a pas dévoilé l'événement : c'est un résultat possible et légitime.")

    st.subheader("Phases")
    visited = set(fb.phases_visited)
    violated = {v.phase for v in fb.phase_violations}
    chips = []
    for p in PHASE_ORDER:
        color = "#c62828" if p in violated else ("#2e7d32" if p in visited else "#9e9e9e")
        chips.append(chip(PHASE_LABELS[p], color))
    st.markdown(" → ".join(chips), unsafe_allow_html=True)
    for v in fb.phase_violations:
        where = f"tour {v.turn}" if v.turn else "fin de l'entretien"
        st.warning(f"{VIOLATION_LABELS[v.kind]} — {PHASE_LABELS[v.phase]}, {where}{' — ' + v.detail if v.detail else ''}")

    if ct.entries:
        st.subheader("Faux détails introduits")
        for e in ct.entries:
            st.error(f"« {e.value} » — tour {e.source_turn} ({TYPE_LABELS[e.source_type]}) : « {e.source_utterance} »")
    for f in fb.lucky_suggestions:
        st.warning(f"Tour {f.turn} : suggestion tombée juste (faute de technique) — « {f.utterance} »")
    for f in fb.off_protocol:
        st.warning(f"Tour {f.turn} : énoncé hors protocole — « {f.utterance} »")

    if rc.elicited:
        with st.expander(f"Informations recueillies ({rc.revealed}/{rc.total})"):
            for e in rc.elicited:
                st.write(f"Tour {e.turn} — {TYPE_LABELS[e.question_type]} — {e.value} ({e.centrality})")

    ls = fb.learner_summary
    if ls is not None:
        st.subheader("Votre synthèse")
        st.write(f"{'—' if ls.recall is None else f'{ls.recall:.0%}'} des faits dits par l'enfant retenus "
                 f"({len(ls.retained_true)}/{ls.true_said}).")
        for i in ls.retained_contaminated:
            st.error(f"Faux détail repris comme un fait : {i}")
        for item in ls.not_said_by_child:
            st.error(f"Jamais dit par l'enfant : « {item} »")

    if fb.rephrasings:
        st.subheader("Reformulations proposées")
        st.caption("Générées automatiquement par le modèle de langue : à lire avec esprit critique.")
        for r in fb.rephrasings:
            st.markdown(f"**Tour {r.turn}** ({TYPE_LABELS[r.question_type]}) « {r.question} »  \n→ *« {r.suggestion} »*")

    st.subheader("Transcription annotée")
    for line in fb.transcript:
        flags = " ".join(chip(f, "#424242") for f in line.flags)
        st.markdown(
            f"{chip(TYPE_LABELS[line.question_type], TYPE_COLORS[line.question_type])} "
            f"<small>{PHASE_LABELS[line.phase]}</small> **{line.turn}.** {line.interviewer} {flags}<br>"
            f"&nbsp;&nbsp;&nbsp;↳ <i>{line.child}</i>",
            unsafe_allow_html=True,
        )


if "feedback" in st.session_state:
    show_feedback(st.session_state.feedback)
    st.stop()

if st.session_state.get("ending"):
    st.header("Fin de l'entretien")
    summary = st.text_area(
        "Synthèse (facultative) : rédigez ce que l'enfant vous a appris. Elle sera confrontée à ses déclarations.",
        key="summary",
    )
    col1, col2 = st.columns(2)
    if col1.button("Voir le retour", type="primary"):
        with st.spinner("Analyse de l'entretien…"):
            log = session.end(learner_summary=summary or None)
        st.session_state.feedback = log.feedback
        st.rerun()
    if col2.button("Reprendre l'entretien"):
        st.session_state.ending = False
        st.rerun()
    st.stop()


# -- interview ---------------------------------------------------------------------

chat_col, trainer_col = st.columns([3, 2]) if trainer else (st.container(), None)

with chat_col:
    st.subheader(f"Entretien avec {profile.name}")
    if isinstance(session.classifier, ManualClassifier):
        with st.expander("Classification manuelle : syntaxe"):
            st.code(HELP)
    for t in st.session_state.turns:
        with st.chat_message("user"):
            st.write(t["interviewer"])
        with st.chat_message("assistant", avatar="🧒"):
            st.write(t["child"])
        for n in t["notices"]:
            st.info(n)
    prompt = st.chat_input("Votre énoncé…")
    if prompt:
        try:
            with st.spinner(f"{profile.name} réfléchit…"):
                result = session.turn(prompt)
        except ManualClassificationError as e:
            st.error(str(e))
        except LLMError as e:
            st.error(f"Modèle de langue injoignable : {e}")
        else:
            st.session_state.turns.append(
                {
                    "interviewer": result.classification.clean_text or prompt,
                    "child": result.response,
                    "notices": result.notices,
                }
            )
            st.rerun()

if trainer_col is not None:
    with trainer_col:
        st.subheader("Mode formateur")
        st.markdown(f"Phase courante : {chip(PHASE_LABELS[session.phase], '#1565c0')}", unsafe_allow_html=True)
        state = session.state
        st.progress(min(1.0, state.reluctance), text=f"Réticence {state.reluctance:.2f}")
        st.progress(min(1.0, state.verbosity), text=f"Verbosité {state.verbosity:.2f}")
        st.progress(min(1.0, state.acquiescence), text=f"Acquiescement {state.acquiescence:.2f}")
        if not state.disclosed:
            st.caption(f"Pas encore de dévoilement — pression {state.disclosure_pressure:.1f}")
        if session.log.turns:
            last = session.log.turns[-1]
            c, d = last.classification, last.decision
            st.markdown("**Dernier tour**")
            st.markdown(
                f"{chip(TYPE_LABELS[c.type], TYPE_COLORS[c.type])} "
                f"{'→ `' + c.target + '`' if c.target else ''} "
                f"{'(' + TYPE_LABELS[c.inner_type] + ')' if c.inner_type else ''}",
                unsafe_allow_html=True,
            )
            if c.suggested_proposition:
                st.caption(f"Proposition suggérée : {c.suggested_proposition}")
            st.caption(f"Décision : {d.speech_act} — {d.reason}")
            if last.fallback_used:
                st.caption("Filtre de sortie : réponse de repli utilisée.")
            st.caption(f"Latence : {last.latency_s.get('total', 0):.1f} s")
        st.markdown(f"**Unités révélées** ({len([u for u in state.revealed if scenario.is_target_unit(u)])}"
                    f"/{len(list(scenario.target_units()))})")
        for uid in state.revealed:
            unit = scenario.unit(uid)
            st.caption(f"✓ {uid} — {unit.value}")
        if state.contaminated:
            st.markdown("**Faux détails**")
            for cu in state.contaminated:
                st.caption(f"✗ {cu.id} — {cu.value} (tour {cu.source_turn}{', intégré' if cu.integrated else ''})")
        for v in session.phases.violations:
            st.warning(f"{VIOLATION_LABELS[v.kind]} ({PHASE_LABELS[v.phase]}, tour {v.turn})")
