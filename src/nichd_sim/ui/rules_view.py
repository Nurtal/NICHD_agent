"""Model control panel: the child's behaviour rules, switched on or off and adjusted, with their sources.

The configuration lives in `st.session_state.rule_config` (a RuleConfig) and applies to the next interview.
Widgets only mirror it: Streamlit forgets the state of widgets that are not drawn (another view), so each
change is written back to the configuration by a callback, and the widgets are redrawn from it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from nichd_sim.parameters import Parameter, Parameters
from nichd_sim.rules import Catalogue, ParamSpec, Rule, RuleConfig, RuleError, list_presets, load_catalogue
from nichd_sim.scenario import AgeBand, ExpressionStyle

BAND_LABELS = {AgeBand.B4_6: "4–6 ans", AgeBand.B7_9: "7–9 ans", AgeBand.B10_12: "10–12 ans"}
EVIDENCE_COLORS = {"tendance publiée": "#2e7d32", "choix de modélisation": "#757575"}
WIDGET_PREFIXES = ("rule:", "param:")
KEY_LABELS = {
    "arousal": "activation", "confusion": "confusion", "base": "fond", "tension": "tension",
    "breathing": "respiration", "tremor": "tremblement", "withdrawal": "retrait", "freeze": "figement",
    "retrieval": "mémoire", "affect": "émotion", "deception": "mensonge", "who": "qui", "what": "quoi",
    "where": "où", "when": "quand", "frequency": "combien de fois", "dont_know": "« je sais pas »",
    "confabulate": "invention", "compound": "question composée", "many_options": "3 options ou plus",
    "omission": "omission", "false_deny": "faux démenti", "feigned_ignorance": "ignorance feinte",
    "minimization": "minimisation", "cover_story": "histoire de couverture", "target_central": "fait central",
    "target_other": "autre fait", "pressure": "pression", "pressure_target": "pression sur les faits",
    "phase_violation": "écart au protocole", "lie": "mensonge", "support": "soutien", "rapport": "rapport",
    "narrative_practice": "pratique narrative", "invitation": "invitation", "cued_invitation": "invitation ciblée",
    "facilitator": "relance", "directive": "directive", "option_posing": "choix", "suggestive": "suggestive",
}


def config() -> RuleConfig:
    if "rule_config" not in st.session_state:
        st.session_state.rule_config = RuleConfig()
    return st.session_state.rule_config


def set_config(cfg: RuleConfig) -> None:
    """Replace the configuration and forget the widgets, so that they are redrawn from it."""
    st.session_state.rule_config = cfg
    for key in [k for k in st.session_state if isinstance(k, str) and k.startswith(WIDGET_PREFIXES)]:
        del st.session_state[key]


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:g}".replace(".", ",")
    if isinstance(v, (list, tuple)):
        return " – ".join(_fmt(x) for x in v)
    if isinstance(v, dict):
        return ", ".join(f"{k} {_fmt(x)}" for k, x in v.items())
    return str(v)


def _chip(text: str, color: str) -> str:
    return (f"<span style='background:{color};color:white;border-radius:0.6em;padding:0.05em 0.55em;"
            f"font-size:0.75em;white-space:nowrap'>{text}</span>")


# -- reading and writing one parameter -------------------------------------------------


def _default(p: Parameter, band: AgeBand) -> Any:
    return p.for_band(band)


def _current(name: str, band: AgeBand, cfg: RuleConfig) -> Any:
    return Parameters.load(band, cfg.overrides)[name]


def _store(name: str, value: Any, band: AgeBand, table: dict[str, Parameter]) -> None:
    """Write one parameter's value for `band` into the configuration (removed when back to default)."""
    cfg = config()
    p = table[name]
    overrides = dict(cfg.overrides)
    if p.values is not None:  # per age band: only this band changes
        per_band = dict(overrides.get(name) or {}) if isinstance(overrides.get(name), dict) else {}
        if value == p.values[band]:
            per_band.pop(band.value, None)
        else:
            per_band[band.value] = value
        if per_band:
            overrides[name] = per_band
        else:
            overrides.pop(name, None)
    elif value == p.value:
        overrides.pop(name, None)
    else:
        overrides[name] = value
    st.session_state.rule_config = cfg.model_copy(update={"overrides": overrides})


def _on_param(name: str, key: str, band: AgeBand, table: dict[str, Parameter], dict_key: str | None = None):
    def cb() -> None:
        value = st.session_state[key]
        if isinstance(value, tuple):
            value = list(value)
        if dict_key is not None:
            value = {**_current(name, band, config()), dict_key: value}
        _store(name, value, band, table)
    return cb


def _on_rule(rule_id: str, key: str):
    def cb() -> None:
        cfg = config()
        disabled = set(cfg.disabled)
        if st.session_state[key]:
            disabled.discard(rule_id)
        else:
            disabled.add(rule_id)
        st.session_state.rule_config = cfg.model_copy(update={"disabled": sorted(disabled)})
    return cb


def _number(x: float, step: float) -> float | int:
    return int(round(x)) if float(step).is_integer() else float(x)


def _widget(name: str, spec: ParamSpec, band: AgeBand, table: dict[str, Parameter], disabled: bool) -> None:
    """One parameter's control, for the current age band."""
    p = table[name]
    cfg = config()
    value, default = _current(name, band, cfg), _default(p, band)
    changed = value != default
    label = spec.label + (" ✎" if changed else "")
    per_band = f" (bande {BAND_LABELS[band]})" if p.values is not None else ""
    help_ = f"{' '.join(p.description.split())}\n\nDéfaut{per_band} : {_fmt(default)}. Paramètre `{name}`."
    key = f"param:{band.value}:{name}"
    if isinstance(value, bool):
        st.toggle(label, value=value, key=key, help=help_, disabled=disabled,
                  on_change=_on_param(name, key, band, table))
    elif isinstance(value, str):
        options = [s.value for s in ExpressionStyle]
        st.selectbox(label + per_band, options, index=options.index(value), key=key, help=help_, disabled=disabled,
                     on_change=_on_param(name, key, band, table))
    elif spec.range is None:
        st.markdown(f"{label} : `{_fmt(value)}`", help=help_)
    elif isinstance(value, dict):
        lo, hi, step = spec.range
        st.markdown(f"**{label}**{per_band}", help=help_)
        cols = st.columns(min(3, len(value)))
        for i, (k, v) in enumerate(value.items()):
            dkey = f"{key}:{k}"
            with cols[i % len(cols)]:
                st.slider(KEY_LABELS.get(k, k) + (" ✎" if v != default.get(k) else ""), _number(lo, step), _number(hi, step),
                          _number(v, step), _number(step, step), key=dkey, disabled=disabled,
                          on_change=_on_param(name, dkey, band, table, dict_key=k))
    elif isinstance(value, list):
        lo, hi, step = spec.range
        st.slider(label + per_band, _number(lo, step), _number(hi, step), tuple(_number(x, step) for x in value),
                  _number(step, step), key=key, help=help_, disabled=disabled,
                  on_change=_on_param(name, key, band, table))
    else:
        lo, hi, step = spec.range
        st.slider(label + per_band, _number(lo, step), _number(hi, step), _number(value, step), _number(step, step),
                  key=key, help=help_, disabled=disabled, on_change=_on_param(name, key, band, table))


# -- one rule ----------------------------------------------------------------------------


def _sources(rule: Rule, catalogue: Catalogue, table: dict[str, Parameter]) -> None:
    if rule.refs:
        lines = []
        for ref in rule.refs:
            r = catalogue.references[ref]
            lines.append(f"- [{r.cite}]({r.url})" if r.url else f"- {r.cite}")
        st.markdown("\n".join(lines))
    else:
        st.caption("Pas de référence directe : valeur choisie pour le modèle.")


def _rule_card(rule: Rule, catalogue: Catalogue, band: AgeBand, table: dict[str, Parameter]) -> None:
    cfg = config()
    on = rule.id not in cfg.disabled
    with st.container(border=True):
        head, badge = st.columns([5, 2])
        with head:
            if rule.toggle:
                key = f"rule:{rule.id}"
                st.checkbox(f"**{rule.title}**", value=on, key=key, on_change=_on_rule(rule.id, key))
            else:
                st.markdown(f"**{rule.title}**", help="Mécanique de base : réglable, mais pas désactivable.")
        with badge:
            st.markdown(_chip(rule.evidence, EVIDENCE_COLORS[rule.evidence]), unsafe_allow_html=True)
        st.caption(" ".join(rule.summary.split()))
        primary = {n: s for n, s in rule.params.items() if s.primary}
        advanced = {n: s for n, s in rule.params.items() if not s.primary}
        for name, spec in primary.items():
            _widget(name, spec, band, table, disabled=not on)
        with st.expander("Sources et réglages avancés"):
            _sources(rule, catalogue, table)
            for name, spec in advanced.items():
                _widget(name, spec, band, table, disabled=not on)
            st.caption("Sources des valeurs, paramètre par paramètre :")
            for name in rule.params:
                st.caption(f"`{name}` — {' '.join(table[name].source.split())}")


# -- the view -------------------------------------------------------------------------------


def _preset_bar(presets_dir: Path) -> None:
    presets = list_presets(presets_dir)
    cfg = config()
    load_col, save_col, reset_col = st.columns([3, 3, 1.4])
    with load_col:
        options = ["—", *presets]
        chosen = st.selectbox("Préréglage", options, key="preset_choice",
                              index=options.index(cfg.name) if cfg.name in presets else 0)
        if st.button("Charger", disabled=chosen == "—", key="preset_load"):
            try:
                set_config(RuleConfig.load(presets[chosen]))
                st.rerun()
            except RuleError as e:
                st.error(str(e))
    with save_col:
        name = st.text_input("Enregistrer sous", value=cfg.name or "", key="preset_name",
                             placeholder="ex. enfant-tres-suggestible")
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.strip().lower()).strip("-")
        if st.button("Enregistrer", disabled=not slug, key="preset_save"):
            saved = cfg.model_copy(update={"name": name.strip()})
            saved.save(presets_dir / f"{slug}.yaml")
            st.session_state.rule_config = saved
            st.toast(f"Préréglage enregistré : {presets_dir / f'{slug}.yaml'}")
    with reset_col:
        st.write("")
        st.write("")
        if st.button("Réinitialiser", key="preset_reset", help="Toutes les règles actives, valeurs par défaut."):
            set_config(RuleConfig())
            st.rerun()


def render(band: AgeBand, presets_dir: Path, session_rules: RuleConfig | None) -> None:
    """`band`: the age band of the chosen scenario's child (what the sliders adjust). `session_rules`: the
    configuration of the interview in progress, if any."""
    catalogue = load_catalogue()
    table = Parameters.load(band).table
    cfg = config()
    _preset_bar(presets_dir)
    switchable = [r for r in catalogue.rules.values() if r.toggle]
    active = sum(r.id not in cfg.disabled for r in switchable)
    adjusted = len(cfg.overrides)
    a, b, c = st.columns(3)
    a.metric("Règles actives", f"{active} / {len(switchable)}")
    b.metric("Paramètres modifiés", adjusted)
    c.metric("Bande d'âge réglée", BAND_LABELS[band])
    if session_rules is not None and session_rules.model_dump(exclude={"name", "description"}) != cfg.model_dump(
        exclude={"name", "description"}
    ):
        st.info("Ces réglages diffèrent de l'entretien en cours : ils s'appliqueront au prochain entretien.")
    else:
        st.caption("Les réglages s'appliquent au prochain entretien (« Nouvel entretien »). Les curseurs d'un "
                   "paramètre par âge ne règlent que la bande de l'enfant du scénario choisi.")
    f_col, q_col = st.columns([3, 2])
    families = f_col.multiselect("Familles", list(catalogue.families), format_func=catalogue.families.get,
                                 key="rules_families", placeholder="Toutes les familles")
    query = q_col.text_input("Rechercher", key="rules_query", placeholder="regard, suggestion, mensonge…").strip().lower()
    for family, rules in catalogue.by_family().items():
        if families and family not in families:
            continue
        shown = [r for r in rules if not query or query in (r.title + " " + r.summary).lower()
                 or any(query in s.label.lower() or query in n for n, s in r.params.items())]
        if not shown:
            continue
        st.subheader(catalogue.families[family])
        cols = st.columns(2)
        for i, rule in enumerate(shown):
            with cols[i % 2]:
                _rule_card(rule, catalogue, band, table)
