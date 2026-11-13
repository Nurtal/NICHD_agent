"""Replay and coder export (#7)."""

import csv

import pytest

from doubles import S01, C, ScriptedClassifier, ask, make_session
from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.llm import ChatResult
from nichd_sim.realization import LLMRealizer
from nichd_sim.replay import CODER_COLUMNS, ReplayError, export_for_coders, find_scenario, load_log, replay
from nichd_sim.scenario import load_scenario
from nichd_sim.session import Session

SCRIPT = [
    ("Bonjour Léo.", C("support", phase_hints=["rapport"])),
    ("Raconte ton anniversaire.", C("invitation", phase_hints=["narrative_practice"])),
    ("Dis-moi pourquoi tu es là.", C("invitation", phase_hints=["transition"])),
    ("Il l'a frappé avec un bâton, hein ?", C("suggestive", "d_pousse", suggested_proposition="il l'a frappé avec un bâton")),
    ("C'était le matin ou le soir ?", C("option_posing", "b_quand", options=["le matin", "le soir"])),
    ("Il avait quelle voiture ?", C("directive", OUT_OF_SCENARIO)),
    ("Et après ?", C("invitation")),
]


class CountingChat:
    """Fake LLM whose answers depend on the call count (would differ if re-called)."""

    model = "counting"

    def __init__(self):
        self.n = 0

    def chat(self, messages, *, temperature, seed=None, think=False, format=None):
        self.n += 1
        # Echo the facts listed in the prompt so the filter accepts most answers.
        facts = [ln.split(". ", 1)[1] for ln in messages[0]["content"].splitlines() if ln[:1].isdigit()]
        return ChatResult(content=(" ".join(facts) or "Je sais pas.") + f" ({self.n})", meta={"seed": seed})


def run(seed=7, log_dir=None):
    clf = ScriptedClassifier()
    s = Session(load_scenario(S01), clf, LLMRealizer(CountingChat(), seed=seed), seed=seed, log_dir=log_dir)
    for u, c in SCRIPT:
        ask(s, clf, u, c)
    return s, s.end()


def test_same_seed_and_script_produce_identical_decisions():
    _, a = run(seed=11)
    _, b = run(seed=11)
    assert [t.decision for t in a.turns] == [t.decision for t in b.turns]
    assert [t.phase for t in a.turns] == [t.phase for t in b.turns]
    assert [t.state_after for t in a.turns] == [t.state_after for t in b.turns]


def test_different_seeds_can_diverge():
    decisions = {tuple(t.decision.speech_act for t in run(seed=k)[1].turns) for k in range(30)}
    assert len(decisions) > 1


def test_replay_reproduces_the_session_without_calling_the_llm(tmp_path):
    _, original = run(seed=5, log_dir=tmp_path)
    log = load_log(next(tmp_path.glob("session_*.json")))
    report = replay(log, load_scenario(S01))
    assert report.identical, report.mismatches
    assert report.turns == len(SCRIPT)
    assert [t.response for t in report.replayed.turns] == [t.response for t in original.turns]
    assert report.replayed.components["classifier"] == "_LoggedClassifier"


def test_replay_uses_logged_parameters_not_current_defaults():
    # Original session ran with overrides making the child always acquiesce.
    forced = load_scenario(S01).model_copy(
        update={"parameter_overrides": {"p_acquiesce": 1.0, "suggestibility_multiplier_range": [1, 1]}}
    )
    clf = ScriptedClassifier()
    s = Session(forced, clf, LLMRealizer(CountingChat(), seed=1), seed=1)
    for u, c in SCRIPT:
        ask(s, clf, u, c)
    original = s.end()
    assert any(t.decision.new_contamination for t in original.turns)
    # Replayed against the plain scenario (default parameters): the logged values must win.
    assert replay(original, load_scenario(S01)).identical


def test_replay_detects_a_tampered_log():
    _, original = run(seed=5)
    tampered = original.model_copy(deep=True)
    tampered.turns[2].response = "autre chose"
    report = replay(tampered, load_scenario(S01))
    assert not report.identical and "tour 3 : response diffère" in report.mismatches


def test_find_scenario_by_id_and_version(tmp_path):
    _, log = run()
    assert find_scenario(log, S01.parent).id == "s01_bagarre_parc"
    wrong = log.model_copy(update={"scenario_version": "9.9.9"})
    with pytest.raises(ReplayError, match="version"):
        find_scenario(wrong, S01.parent)


def test_coder_export_is_a_blank_transcript(tmp_path):
    s, clf, _ = make_session()
    from nichd_sim.classifiers.manual import ManualClassifier

    s.classifier = ManualClassifier()
    s.turn("[inv] Raconte-moi tout.")
    s.turn("[sug:d_pousse=il l'a tapé] Il l'a tapé, hein ?")
    path = export_for_coders(s.end(), tmp_path / "codage.csv")
    raw = path.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(raw.splitlines(), delimiter=";"))
    assert rows[0] == CODER_COLUMNS
    assert rows[1] == ["1", "interviewer", "Raconte-moi tout.", ""]
    assert rows[2][1] == "enfant" and rows[2][3] == ""
    assert rows[3][2] == "Il l'a tapé, hein ?"  # manual tag stripped
    for banned in ("invitation", "suggestive", "[inv]", "d_pousse", "substantive"):
        assert banned not in raw


def test_unreadable_log_gives_a_clear_error(tmp_path):
    bad = tmp_path / "old.json"
    bad.write_text('{"session_id": "x"}')
    with pytest.raises(ReplayError, match="format"):
        load_log(bad)
    with pytest.raises(ReplayError, match="introuvable"):
        load_log(tmp_path / "absent.json")
