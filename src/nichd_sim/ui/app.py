"""Streamlit interface: interview, trainer mode and feedback screen.

All behaviour goes through the public Session API; this module only displays.
Run with:  uv run nichd-sim ui   (or: uv run streamlit run src/nichd_sim/ui/app.py)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st

from nichd_sim.classifiers.llm import DEFAULT_CLASSIFIER_THINK, LLMClassifier
from nichd_sim.classifiers.manual import HELP, ManualClassificationError, ManualClassifier
from nichd_sim.demeanor import STYLE_LABELS, stage_direction
from nichd_sim.engine import SpeechAct
from nichd_sim.evaluation import load_scenarios
from nichd_sim.feedback import PHASE_LABELS, TYPE_LABELS, WAIT_LABEL, LLMRephraser, LLMSummaryMatcher
from nichd_sim.llm import DEFAULT_MODEL, DEFAULT_URL, LLMError, OllamaClient
from nichd_sim.phases import ORDER as PHASE_ORDER
from nichd_sim.phases import VIOLATION_LABELS
from nichd_sim.realization import LLMRealizer, TemplateRealizer
from nichd_sim.rules import RuleConfig
from nichd_sim.scenario import ExpressionStyle
from nichd_sim.session import Session
from nichd_sim.ui import engine_view, flow_view, rules_view

SCENARIOS_DIR = Path(os.environ.get("NICHD_SCENARIOS", Path(__file__).resolve().parents[3] / "scenarios"))
LOG_DIR = os.environ.get("NICHD_LOG_DIR", "sessions")
PRESETS_DIR = Path(os.environ.get("NICHD_PRESETS", Path(__file__).resolve().parents[3] / "presets"))
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


def new_session(scenario, seed: int, offline: bool, rules: RuleConfig | None = None) -> Session:
    if offline:
        classifier, realizer, rephraser, matcher = ManualClassifier(), TemplateRealizer(), None, None
    else:
        client = OllamaClient(DEFAULT_MODEL, DEFAULT_URL)
        think = os.environ.get("NICHD_CLASSIFIER_THINK", DEFAULT_CLASSIFIER_THINK)
        classifier = LLMClassifier(client, think=False if think == "off" else think)
        realizer = LLMRealizer(client, seed=seed)
        rephraser, matcher = LLMRephraser(client), LLMSummaryMatcher(client)
    rules = rules or RuleConfig()
    params = rules.parameters(scenario.child_profile.age_band, scenario.parameter_overrides)
    return Session(
        scenario, classifier, realizer, seed=seed, rephraser=rephraser, summary_matcher=matcher, log_dir=LOG_DIR,
        params=params, rules=rules.summary(),
    )


def reset():
    for key in ("session", "turns", "ending", "feedback", "session_rules"):
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
    with st.expander("Profil de l'enfant"):
        st.caption("Ajustements appliqués au prochain entretien.")
        reluctance = st.slider("Réticence", 0.0, 1.0, profile.reluctance, 0.05, key=f"{chosen}:reluctance")
        verbal = st.slider("Compétences verbales", 0.0, 1.0, profile.verbal_skills, 0.05, key=f"{chosen}:verbal")
        suggest = st.slider("Suggestibilité", 0.0, 1.0, profile.suggestibility, 0.05, key=f"{chosen}:suggest")
        styles = ["auto", *ExpressionStyle]
        style = st.selectbox(
            "Style d'expression", styles, key=f"{chosen}:style",
            index=styles.index(profile.expression_style) if profile.expression_style else 0,
            format_func=lambda v: "selon l'âge" if v == "auto" else STYLE_LABELS[v],
        )
        strength = None
        if scenario.deception is not None:
            strength = st.slider("Force de la dissimulation", 0.0, 1.0, scenario.deception.strength, 0.05,
                                 key=f"{chosen}:strength")
    adjusted = scenario.model_copy(update={"child_profile": profile.model_copy(update={
        "reluctance": reluctance, "verbal_skills": verbal, "suggestibility": suggest,
        "expression_style": None if style == "auto" else ExpressionStyle(style),
    })})
    if strength is not None:
        adjusted = adjusted.model_copy(update={"deception": scenario.deception.model_copy(update={"strength": strength})})
    seed = st.number_input("Graine (reproductibilité)", min_value=0, value=0, step=1, key="seed")
    offline = st.toggle("Mode hors ligne (sans LLM)", value=OFFLINE, key="offline",
                        help="Voix gabarit et classification manuelle par préfixes.")
    trainer = st.toggle("Mode formateur", value=False, key="trainer")
    rule_config = rules_view.config()
    if not rule_config.is_default:
        st.caption(f"Règles du modèle : {rule_config.name or 'réglages personnalisés'} · "
                   f"{len(rule_config.disabled)} désactivée(s) · {len(rule_config.overrides)} paramètre(s) modifié(s)")
    if st.button("Nouvel entretien", type="primary", use_container_width=True):
        reset()
        st.session_state.session = new_session(adjusted, int(seed), offline, rule_config)
        st.session_state.session_rules = rule_config
        st.session_state.turns = []
        st.rerun()
    if "session" in st.session_state and "feedback" not in st.session_state:
        if st.button("Terminer l'entretien", use_container_width=True):
            st.session_state.ending = True
            st.rerun()

session: Session | None = st.session_state.get("session")

VIEWS = ["Entretien", "Moteur en direct", "Graphe du système", "Règles du modèle"]
view = st.segmented_control("Vue", VIEWS, default="Entretien", key="view", label_visibility="collapsed")

if view == "Règles du modèle":
    st.caption("Panneau de configuration du modèle : les règles qui dirigent le comportement de l'enfant, tirées "
               "de la littérature. Cochez ou décochez une règle, réglez ses coefficients, lisez ses sources.")
    rules_view.render(profile.age_band, PRESETS_DIR, st.session_state.get("session_rules"))
    st.stop()

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
            st.error(f"Faux détail repris comme un fait : « {fb.false_detail(i)} » ({i})")
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
            f"&nbsp;&nbsp;&nbsp;↳ {'<small>(' + line.stage_direction + ')</small> ' if line.stage_direction else ''}"
            f"<i>{line.child}</i>",
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


def submit(prompt: str | None, on_step=None) -> None:
    """One interviewer utterance, from any view (None: wait in silence). `on_step`: live display of the
    turn's steps."""
    try:
        with st.spinner(f"{session.scenario.child_profile.name} réfléchit…"):
            result = session.wait(on_step=on_step) if prompt is None else session.turn(prompt, on_step=on_step)
    except ManualClassificationError as e:
        st.error(str(e))
    except LLMError as e:
        st.error(f"Modèle de langue injoignable : {e}")
    else:
        st.session_state.turns.append(
            {
                "interviewer": WAIT_LABEL if prompt is None else (result.classification.clean_text or prompt),
                "child": result.response,
                "stage": stage_direction(
                    result.decision.demeanor, result.decision.delivery,
                    silent=result.decision.speech_act == SpeechAct.SILENCE, text=result.response,
                ),
                "notices": result.notices,
            }
        )
        st.rerun()


def conversation(key: str, on_step=None) -> None:
    if isinstance(session.classifier, ManualClassifier):
        with st.expander("Classification manuelle : syntaxe"):
            st.code(HELP)
    for t in st.session_state.turns:
        with st.chat_message("user"):
            st.write(t["interviewer"])
        with st.chat_message("assistant", avatar="🧒"):
            if t.get("stage"):
                st.caption(f"*{t['stage']}*")
            st.write(t["child"])
        for n in t["notices"]:
            st.info(n)
    if st.session_state.turns and st.button(
        "Attendre", key=f"{key}_wait", help="Laisser un silence, sans rien dire : l'enfant peut compléter sa réponse."
    ):
        submit(None, on_step=on_step)
    prompt = st.chat_input("Votre énoncé…", key=key)
    if prompt:
        submit(prompt, on_step=on_step)


# Pause after each step of the live map, so that the eye can follow it (the engine itself takes
# milliseconds; the LLM steps take seconds on their own). "decided" lets the engine path play out.
FLOW_DWELL_S = {"classify": 0.3, "classified": 0.5, "decided": 1.8, "filtered": 0.6, "fallback": 0.6}


def live_map(slot):
    """Step listener redrawing the system map while the turn runs."""
    state = flow_view.FlowState(deception=session.scenario.deception is not None)
    shown: set[str] = set()

    def on_step(step: str, data: dict) -> None:
        state.on_step(step, data)
        lit = set(flow_view.lit_nodes(state))
        slot.html(flow_view.render(state, fresh=lit - shown))
        shown.update(lit)
        if step == "done":
            st.session_state.flow_static = True  # already played: no replay after the rerun
        time.sleep(FLOW_DWELL_S.get(step, 0))

    return on_step


if view == "Graphe du système":
    st.caption("Carte du système : le chemin du tour s'allume pendant qu'il est traité. Bleu : règles déterministes · "
               "violet : appels au LLM · pointillés : données · grisé : non emprunté à ce tour.")
    chat, graph = st.columns([1.4, 5])
    with graph:
        slot = st.empty()
        deception = session.scenario.deception is not None
        if session.log.turns:
            last = flow_view.FlowState.from_record(session.log.turns[-1], session.phases.violations, deception)
            slot.html(flow_view.render(last, fresh=set() if st.session_state.pop("flow_static", False) else None))
        else:
            slot.html(flow_view.render(flow_view.FlowState(deception=deception)))
    with chat, st.container(height=760, border=False):
        st.subheader(f"Entretien avec {session.scenario.child_profile.name}")
        conversation("graph_input", on_step=live_map(slot))
    st.stop()

if view == "Moteur en direct":
    st.caption("Vue de démonstration et de débogage : ce que le moteur de comportement décide à chaque tour.")
    chat, engine = st.columns([2, 5])
    with chat, st.container(height=900, border=False):
        st.subheader(f"Entretien avec {session.scenario.child_profile.name}")
        conversation("engine_input")
    with engine:
        engine_view.render(session, TYPE_COLORS)
    st.stop()

chat_col, trainer_col = st.columns([3, 2]) if trainer else (st.container(), None)

with chat_col:
    st.subheader(f"Entretien avec {session.scenario.child_profile.name}")
    conversation("chat_input")

# Keep the trainer panel in view while the conversation grows (sticky within its column).
TRAINER_PANEL_CSS = (
    "<style>[data-testid='stColumn']:has(.st-key-trainer_panel)"
    "{position:sticky;top:3.75rem;align-self:flex-start;z-index:1;"
    "max-height:calc(100vh - 13rem);overflow-y:auto}</style>"
)

if trainer_col is not None:
    st.markdown(TRAINER_PANEL_CSS, unsafe_allow_html=True)
    with trainer_col, st.container(key="trainer_panel"):
        st.subheader("Mode formateur")
        st.markdown(f"Phase courante : {chip(PHASE_LABELS[session.phase], '#1565c0')}", unsafe_allow_html=True)
        state = session.state
        st.progress(min(1.0, state.reluctance), text=f"Réticence {state.reluctance:.2f}")
        st.progress(min(1.0, state.verbosity), text=f"Verbosité {state.verbosity:.2f}")
        st.progress(min(1.0, state.acquiescence), text=f"Acquiescement {state.acquiescence:.2f}")
        st.progress(min(1.0, state.arousal), text=f"Activation {state.arousal:.2f} (base {state.arousal_baseline:.2f})")
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
            if d.delivery is not None:
                st.caption(f"Diction : {d.delivery.describe()}")
            if d.demeanor is not None:
                st.caption(f"Corps : {d.demeanor.describe()}")
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
