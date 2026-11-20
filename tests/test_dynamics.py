"""Interaction dynamics (docs/plans/adaptations-litterature.md): the socle of lot 0 — neutral values
for parameters added after log format 3, the engine's memory of the previous turn and of the closed
questions asked, and replay of older logs."""

from pathlib import Path

from doubles import C, ask, make_session

from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.engine import SpeechAct
from nichd_sim.parameters import Parameters, _default_table
from nichd_sim.replay import find_scenario, replay
from nichd_sim.scenario import AgeBand
from nichd_sim.session import SessionLog

ROOT = Path(__file__).resolve().parent.parent
FORMAT3_PARAMETERS = set((ROOT / "tests" / "fixtures" / "parameters_format3.txt").read_text().split())


# -- neutral values -------------------------------------------------------------


def test_every_parameter_added_after_format_3_has_a_neutral_value():
    """Older logs do not list it: without a neutral value, its rule would change their decisions."""
    added = set(_default_table()) - FORMAT3_PARAMETERS
    missing = sorted(name for name in added if not _default_table()[name].has_neutral)
    assert not missing, f"paramètres sans valeur neutre : {missing}"


def test_for_log_switches_off_parameters_the_log_does_not_list(tmp_path):
    table = tmp_path / "p.yaml"
    table.write_text(
        "old:\n  description: d\n  source: s\n  estimated: true\n  value: 1\n"
        "new_rule:\n  description: d\n  source: s\n  estimated: true\n  value: 0.3\n  neutral: 0\n"
        "new_plain:\n  description: d\n  source: s\n  estimated: true\n  value: 7\n",
        encoding="utf-8",
    )
    legacy = Parameters.for_log(AgeBand.B7_9, {"old": 2}, path=table)
    assert legacy["old"] == 2  # logged value kept
    assert legacy["new_rule"] == 0  # absent from the log: neutral
    assert legacy["new_plain"] == 7  # no neutral declared: current default
    current = Parameters.for_log(AgeBand.B7_9, {"old": 2, "new_rule": 0.3}, path=table)
    assert current["new_rule"] == 0.3


def test_neutral_value_may_be_zero_or_null(tmp_path):
    table = tmp_path / "p.yaml"
    table.write_text(
        "a:\n  description: d\n  source: s\n  estimated: true\n  value: 1\n  neutral: null\n"
        "b:\n  description: d\n  source: s\n  estimated: true\n  value: 1\n",
        encoding="utf-8",
    )
    params = Parameters.load(AgeBand.B7_9, path=table)
    assert params.table["a"].has_neutral and params.table["a"].neutral is None
    assert not params.table["b"].has_neutral


# -- memory of the interaction ----------------------------------------------------


def test_engine_remembers_the_previous_act_and_target():
    s, clf, _ = make_session(seed=1)
    result = ask(s, clf, "Comment il s'appelait ?", C("directive", OUT_OF_SCENARIO))
    assert s.state.last_act == result.decision.speech_act
    assert s.state.last_target == OUT_OF_SCENARIO
    ask(s, clf, "D'accord.", C("support"))
    assert s.state.last_target is None
    assert s.state.last_act == SpeechAct.ACKNOWLEDGE


def test_closed_questions_are_counted_open_prompts_are_not():
    s, clf, _ = make_session(seed=1)
    ask(s, clf, "Raconte-moi.", C("invitation"))
    ask(s, clf, "Qui a poussé ?", C("directive", "d_pousse"))
    ask(s, clf, "Qui a poussé, alors ?", C("directive", "d_pousse"))  # same unit: a repetition
    assert s.state.closed_asked == {"d_pousse": 2}
    assert s.engine.asked_before == 1


def test_out_of_scenario_questions_are_told_apart_by_their_wording():
    s, clf, _ = make_session(seed=1)
    ask(s, clf, "De quelle couleur était la voiture ?", C("directive", OUT_OF_SCENARIO))
    ask(s, clf, "Comment il s'appelait ?", C("directive", OUT_OF_SCENARIO))
    ask(s, clf, "De quelle couleur était la voiture ?", C("directive", OUT_OF_SCENARIO))
    counts = s.state.closed_asked
    assert sorted(counts.values()) == [1, 2]
    assert all(k.startswith(f"{OUT_OF_SCENARIO}:") for k in counts)


def test_memory_does_not_change_decisions():
    """Lot 0 adds memory only: the decisions are those of the engine before it."""
    s, clf, _ = make_session(seed=4)
    script = [C("support"), C("invitation"), C("directive", "d_pousse"), C("directive", "d_pousse")]
    acts = [ask(s, clf, f"u{i}", c).decision.speech_act for i, c in enumerate(script)]
    log = SessionLog.model_validate_json(s.end().model_dump_json())
    assert replay(log, find_scenario(log, ROOT / "scenarios")).identical
    assert len(acts) == 4


def test_a_format_3_log_without_the_new_fields_still_replays(monkeypatch):
    monkeypatch.chdir(ROOT)
    s, clf, _ = make_session(seed=2)
    for i, c in enumerate([C("support"), C("invitation"), C("directive", "d_pousse"), C("directive", OUT_OF_SCENARIO)]):
        ask(s, clf, f"u{i}", c)
    data = s.end().model_dump(mode="json")
    data["log_format"] = 3
    for t in data["turns"]:
        for name in ("last_act", "last_target", "closed_asked"):
            t["state_after"].pop(name, None)
    log = SessionLog.model_validate(data)
    assert replay(log, find_scenario(log)).identical
