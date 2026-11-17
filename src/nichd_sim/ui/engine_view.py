"""Live view of the behavior engine (debug / demonstration).

For the last turn: classification → phase → rule → allowed units → delivery → body → output
filter. Then the state, its trajectory over the interview, and the scenario's facts. Display
only: everything is read from the session log.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from nichd_sim.delivery import CAUSE_LABELS, HesitationCause
from nichd_sim.demeanor import CUE_LABELS, INTENSITY_LABELS, STYLE_LABELS, stage_direction
from nichd_sim.engine import EngineState, SpeechAct
from nichd_sim.feedback import PHASE_LABELS, SPEECH_ACT_LABELS, TYPE_LABELS
from nichd_sim.phases import ORDER as PHASE_ORDER
from nichd_sim.phases import VIOLATION_LABELS
from nichd_sim.scenario import Centrality, Scenario
from nichd_sim.session import Session


# State variables, in a fixed order with fixed colors (validated categorical slots 1–5).
VARIABLES = {
    "arousal": ("Activation", "#2a78d6"),
    "reluctance": ("Réticence", "#eb6834"),
    "concealment": ("Dissimulation", "#1baf7a"),
    "acquiescence": ("Acquiescement", "#eda100"),
    "verbosity": ("Verbosité", "#e87ba4"),
}

GREEN, AMBER, RED, BLUE, GREY, VIOLET = "#2e7d32", "#ef6c00", "#c62828", "#1565c0", "#757575", "#5e35b1"


def chip(text: str, color: str) -> str:
    return (
        f"<span style='background:{color};color:white;border-radius:0.6em;padding:0.1em 0.6em;"
        f"font-size:0.8em;white-space:nowrap;display:inline-block;margin:0.1em 0'>{text}</span>"
    )


def _html(text: str) -> None:
    st.markdown(text, unsafe_allow_html=True)


def _variables(scenario: Scenario) -> list[str]:
    return [v for v in VARIABLES if v != "concealment" or scenario.deception is not None]


# -- last turn ---------------------------------------------------------------------


def _step(title: str):
    box = st.container(border=True)
    box.markdown(f"**{title}**")
    return box


def last_turn(session: Session, type_colors: dict[str, str]) -> None:
    turn = session.log.turns[-1]
    c, d = turn.classification, turn.decision
    scenario = session.scenario

    with _step(f"1 · Classification de l'énoncé (tour {turn.index})"):
        st.caption(f"« {c.clean_text or turn.utterance} »")
        inner = f" → élément le plus directif : {TYPE_LABELS[c.inner_type]}" if c.inner_type else ""
        bits = [chip(TYPE_LABELS[c.type], type_colors[c.type]) + inner]
        if c.target:
            bits.append(f"cible `{c.target}`")
        if c.suggested_proposition:
            bits.append(f"proposition « {c.suggested_proposition} »")
        if c.options:
            bits.append("options " + " / ".join(f"« {o} »" for o in c.options))
        if c.phase_hints:
            bits.append(f"indice de phase : {PHASE_LABELS.get(c.phase_hints[0], c.phase_hints[0])}")
        _html(" · ".join(bits))

    with _step("2 · Suivi des phases"):
        current = session.phases.phase
        row = []
        for p in PHASE_ORDER:
            if p == current:
                row.append(chip(PHASE_LABELS[p], BLUE))
            elif PHASE_ORDER.index(p) < PHASE_ORDER.index(current):
                row.append(chip(PHASE_LABELS[p], "#90a4ae"))
            else:
                row.append(f"<span style='opacity:0.5;font-size:0.8em'>{PHASE_LABELS[p]}</span>")
        _html(" → ".join(row))
        if turn.asked_in != turn.phase:
            st.caption(f"Question posée en {PHASE_LABELS[turn.asked_in]}, phase après la réponse : {PHASE_LABELS[turn.phase]}")
        for v in session.phases.violations:
            if v.turn == turn.index:
                st.warning(f"⚠ {VIOLATION_LABELS[v.kind]}" + (f" — {v.detail}" if v.detail else ""))

    with _step("3 · Règle du moteur"):
        effective = d.effective_type or c.type
        tags = [chip(f"règle : {TYPE_LABELS[effective]}", type_colors[effective]),
                chip(f"acte : {SPEECH_ACT_LABELS[d.speech_act]}", VIOLET)]
        if d.disclosure:
            tags.append(chip("dévoilement forcé" if d.forced_disclosure else "dévoilement", AMBER if d.forced_disclosure else GREEN))
        if d.lucky_suggestion:
            tags.append(chip("suggestion tombée juste", AMBER))
        if d.new_contamination:
            tags.append(chip(f"contamination {d.new_contamination}", RED))
        if d.lie is not None:
            tags.append(chip(f"mensonge : {d.lie.kind} sur {d.lie.protected}", RED))
        if d.withheld:
            tags.append(chip(f"omis : {', '.join(d.withheld)}", RED))
        if d.retraction is not None:
            tags.append(chip(f"revient sur {d.retraction.id}", GREEN))
        _html(" ".join(tags))
        st.caption(d.reason or "—")

    with _step("4 · Unités autorisées (seules transmises au LLM)"):
        if not d.allowed_units:
            st.caption("Aucune : le LLM ne reçoit aucun fait pour ce tour.")
        out = []
        for au in d.allowed_units:
            if au.lie:
                color, kind = RED, "mensonge"
            elif au.contaminated:
                color, kind = AMBER, "faux détail"
            elif au.new:
                color, kind = GREEN, "nouveau"
            else:
                color, kind = GREY, "déjà dit"
            out.append(f"{chip(kind, color)} `{au.id}` {au.value}")
        if out:
            _html("<br>".join(out))

    with _step("5 · Diction (comment l'enfant le dit)"):
        if d.delivery is None:
            st.caption("Journal antérieur : pas de diction.")
        else:
            loads = d.delivery.loads
            cols = st.columns(len(HesitationCause))
            for col, cause in zip(cols, HesitationCause):
                value = loads.get(cause, 0.0)
                col.progress(min(1.0, value), text=f"{CAUSE_LABELS[cause]} {value:.0%}")
            st.caption(d.delivery.describe())

    with _step("6 · Corps"):
        if d.demeanor is None:
            st.caption("Journal antérieur : pas de comportement non verbal.")
        else:
            cues = " ".join(
                chip(f"{CUE_LABELS[sc.cue]} · {INTENSITY_LABELS[sc.intensity]}", BLUE if i == 0 else GREY)
                for i, sc in enumerate(d.demeanor.cues)
            )
            _html(f"{cues} <small>style {STYLE_LABELS[d.demeanor.style]}</small>")
            stage = stage_direction(d.demeanor, d.delivery, silent=d.speech_act == SpeechAct.SILENCE, text=turn.response)
            if stage:
                st.caption(f"Didascalie : *{stage}*")

    with _step("7 · Réalisation et filtre de sortie"):
        for i, a in enumerate(turn.attempts, 1):
            if a.ok:
                st.caption(f"Essai {i} accepté")
            else:
                why = a.forbidden_terms + a.leaked_units + [f"manque {m}" for m in a.missing_units]
                why += ["vide"] * a.empty + ["trop long"] * a.too_long + ["contredit la décision"] * a.contradicts
                st.caption(f"Essai {i} rejeté ({', '.join(why) or '?'}) : « {a.text} »")
        if turn.fallback_used:
            st.caption("Réponse de repli utilisée.")
        st.markdown(f"> {turn.response}")


# -- state ---------------------------------------------------------------------------


def state_metrics(session: Session) -> None:
    turns = session.log.turns
    after = session.state
    before = turns[-1].state_before if turns else after
    names = _variables(session.scenario)
    cols = st.columns(len(names) + (0 if after.disclosed else 1))
    for col, name in zip(cols, names):
        label, _ = VARIABLES[name]
        now, then = getattr(after, name), getattr(before, name)
        delta = round(now - then, 3)
        col.metric(label, f"{now:.2f}", delta=f"{delta:+.2f}" if delta else None, delta_color="off")
    if not after.disclosed:
        rise = round(after.disclosure_pressure - before.disclosure_pressure, 2)
        cols[-1].metric("Pression de dévoilement", f"{after.disclosure_pressure:.1f}",
                        delta=f"{rise:+.1f}" if rise else None, delta_color="off")
    if turns:
        st.caption(f"Activation de base {after.arousal_baseline:.2f} · style "
                   f"{STYLE_LABELS[session.engine.style]} · unités révélées {len(after.revealed)}")


def _trajectory_frame(session: Session) -> pd.DataFrame:
    turns = session.log.turns
    states: list[tuple[int, EngineState]] = [(0, turns[0].state_before)] + [(t.index, t.state_after) for t in turns]
    rows = []
    for index, state in states:
        for name in _variables(session.scenario):
            rows.append({"tour": index, "variable": VARIABLES[name][0], "valeur": round(getattr(state, name), 3)})
    return pd.DataFrame(rows)


def trajectory(session: Session) -> None:
    if not session.log.turns:
        return
    df = _trajectory_frame(session)
    names = [VARIABLES[n][0] for n in _variables(session.scenario)]
    colors = [VARIABLES[n][1] for n in _variables(session.scenario)]
    scale = alt.Scale(domain=names, range=colors)
    hover = alt.selection_point(fields=["tour"], nearest=True, on="pointerover", empty=False)
    base = alt.Chart(df).encode(
        x=alt.X("tour:Q", title="tour", axis=alt.Axis(tickMinStep=1, grid=False)),
        y=alt.Y("valeur:Q", title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(gridOpacity=0.3)),
        color=alt.Color("variable:N", scale=scale, legend=alt.Legend(orient="top", title=None)),
    )
    lines = base.mark_line(strokeWidth=2, interpolate="monotone")
    points = base.mark_circle(size=64).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("tour:Q"), alt.Tooltip("variable:N"), alt.Tooltip("valeur:Q", format=".2f")],
    ).add_params(hover)
    rule = alt.Chart(df).mark_rule(opacity=0.3).encode(x="tour:Q").transform_filter(hover)
    st.altair_chart((lines + points + rule).properties(height=240), use_container_width=True)
    with st.expander("Valeurs (tableau)"):
        st.dataframe(df.pivot(index="tour", columns="variable", values="valeur")[names], use_container_width=True)


# -- facts ---------------------------------------------------------------------------


def facts(session: Session) -> None:
    scenario, state = session.scenario, session.state
    revealed_at: dict[str, int] = {}
    for t in session.log.turns:
        for au in t.decision.allowed_units:
            if not au.contaminated and not au.lie and au.new and au.id in state.revealed:
                revealed_at.setdefault(au.id, t.index)
    active_lies = {lr.protected: lr for lr in state.lies if lr.retracted_turn is None}
    last = session.log.turns[-1].decision if session.log.turns else None
    just = {au.id for au in last.allowed_units if au.new} if last else set()
    lines = []
    for segment, unit in scenario.target_units():
        if unit.id in active_lies:
            status = chip(f"caché : {active_lies[unit.id].kind}", RED)
        elif unit.id in revealed_at:
            status = chip(f"révélé tour {revealed_at[unit.id]}", GREEN)
        elif scenario.is_protected(unit.id):
            status = chip("protégé, non dit", "#8d6e63")
        else:
            status = chip("non dit", GREY)
        star = " ✦" if unit.id in just else ""
        weight = "**" if unit.centrality == Centrality.CENTRAL else ""
        lines.append(f"{status} <small>{segment}</small> {weight}`{unit.id}`{weight} {unit.value}{star}")
    _html("<br>".join(lines))
    st.caption("En gras : faits centraux. ✦ : livré à ce tour.")
    if state.contaminated:
        st.markdown("**Faux détails**")
        for cu in state.contaminated:
            st.caption(f"✗ {cu.id} — {cu.value} (tour {cu.source_turn}{', intégré' if cu.integrated else ''})")


def render(session: Session, type_colors: dict[str, str]) -> None:
    """The whole live view, for the current session."""
    st.markdown("#### État interne")
    state_metrics(session)
    if not session.log.turns:
        st.info("Posez une première question : chaque étape du moteur s'affichera ici.")
        return
    trajectory(session)
    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### Dernier tour, étape par étape")
        last_turn(session, type_colors)
    with right:
        st.markdown("#### Faits de l'événement cible")
        facts(session)
