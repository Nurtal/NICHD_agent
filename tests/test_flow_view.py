"""System map (UI demo): which nodes light up for a turn."""

from doubles import C, ask, make_session
from test_demeanor import s08

from nichd_sim.scenario import load_scenario
import xml.etree.ElementTree as ET

from nichd_sim.ui.flow_view import LEVELS, FlowState, lit_nodes, render, render_svg
from test_demeanor import S02


def _last(s):
    return FlowState.from_record(s.log.turns[-1], s.phases.violations, s.scenario.deception is not None)


def test_live_steps_light_the_map_in_order():
    s, clf, _ = make_session(load_scenario(S02), seed=0)
    clf.script["q"] = C("support")
    state, seen = FlowState(), []
    s.turn("q", on_step=lambda step, data: (state.on_step(step, data), seen.append((step, lit_nodes(state)))))
    steps = [st for st, _ in seen]
    assert steps[:3] == ["classify", "classified", "decided"] and steps[-1] == "done"
    assert "realize" in steps and "filtered" in steps
    lit_after = dict(seen)
    assert lit_after["classify"] == ["input"]
    assert "decision" in lit_after["decided"] and "realizer" not in lit_after["decided"]
    assert {"output", "log", "effects", "rule6"} <= set(lit_after["done"])


def test_the_turn_is_unchanged_by_the_listener():
    def run(listen):
        s, clf, _ = make_session(load_scenario(S02), seed=3)
        for i, c in enumerate([C("support"), C("invitation"), C("suggestive", "d_bras", suggested_proposition="le cou")]):
            clf.script[f"u{i}"] = c
            s.turn(f"u{i}", on_step=(lambda *a: None) if listen else None)
        return [t.decision for t in s.log.turns]
    assert run(True) == run(False)


def test_only_the_path_taken_lights_up():
    s, clf, _ = make_session(s08(1.0, reluctance=0.0), seed=4)
    for i, c in enumerate([C("support"), C("invitation", phase_hints=["transition"]),
                           C("option_posing", "d_bras", suggested_proposition="bras")]):
        ask(s, clf, f"u{i}", c)
    lit = set(lit_nodes(_last(s)))
    assert "conceal" in lit and "rule4" in lit  # lie on a yes/no question
    assert not {"rule0", "rule5", "contamination", "fallback"} & lit


def test_reluctant_child_stops_at_the_gate():
    s, clf, _ = make_session(load_scenario(S02), seed=0)  # reluctance 0.65
    ask(s, clf, "q", C("invitation", phase_hints=["transition"]))
    lit = set(lit_nodes(_last(s)))
    assert "gate" in lit and not any(n.startswith("rule") for n in lit)


def test_busy_node_pulses_while_the_llm_works():
    state = FlowState(level=LEVELS["classify"], utterance="bonjour")
    assert "class='n llm busy'" in render_svg(state)


def test_render_escapes_user_text():
    s, clf, _ = make_session(load_scenario(S02), seed=0)
    ask(s, clf, "<script>x</script>", C("support"))
    svg = render_svg(_last(s))
    assert "<script>x" not in svg
    ET.fromstring(svg)  # well-formed XML: required for an SVG image


def test_render_is_an_image_streamlit_will_not_sanitize_away():
    html = render(FlowState())
    assert html.startswith("<img") and "data:image/svg+xml;base64," in html
