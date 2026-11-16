"""Delivery (ADR 0002): multi-cause hesitation, separate RNG stream, speech plan, MVP non-regression."""

import random
from pathlib import Path

import pytest
from doubles import C, ask, make_session, with_profile

from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.delivery import (
    FILLER,
    ChunkKind,
    Delivery,
    HesitationCause,
    Volume,
    make_delivery,
    plan_speech,
    render_plan,
)
from nichd_sim.engine import SpeechAct
from nichd_sim.parameters import Parameters
from nichd_sim.replay import find_scenario, load_log, replay
from nichd_sim.scenario import AgeBand, load_scenario
from nichd_sim.session import LOG_FORMAT, SessionLog

ROOT = Path(__file__).resolve().parent.parent
MVP_LOGS = sorted((ROOT / "tests" / "fixtures" / "mvp_logs").glob("*.json"))
S02 = ROOT / "scenarios" / "s02_violences_maison.yaml"

R = HesitationCause


# -- non-regression -----------------------------------------------------------


def test_mvp_fixtures_are_present():
    assert len(MVP_LOGS) == 21


@pytest.mark.parametrize("path", MVP_LOGS, ids=lambda p: p.stem)
def test_mvp_logs_replay_identically(path, monkeypatch):
    """Logs produced by v0.1-mvp: same decisions, responses, phases and states with the new engine."""
    monkeypatch.chdir(ROOT)
    log = load_log(path)
    assert log.log_format == 1
    report = replay(log, find_scenario(log))
    assert report.identical, report.mismatches


def test_format_2_log_round_trips_through_replay(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    s, clf, _ = make_session(load_scenario(S02), seed=3)
    for i, c in enumerate([C("support"), C("invitation"), C("invitation"), C("directive", "b_dimanche"), C("other")]):
        ask(s, clf, f"u{i}", c)
    log = SessionLog.model_validate_json(s.end().model_dump_json())
    assert log.log_format == LOG_FORMAT == 2
    assert all(t.decision.delivery is not None for t in log.turns)
    assert replay(log, find_scenario(log)).identical


# -- determinism ----------------------------------------------------------------


def _deliveries(seed):
    s, clf, _ = make_session(load_scenario(S02), seed=seed)
    return [ask(s, clf, f"u{i}", C("invitation")).decision.delivery for i in range(6)]


def test_delivery_is_deterministic_for_a_seed_and_varies_across_seeds():
    assert _deliveries(1) == _deliveries(1)
    assert _deliveries(1) != _deliveries(2)


# -- causes ---------------------------------------------------------------------


def test_reluctance_hesitation_is_emotional_and_quiet():
    s, clf, _ = make_session(load_scenario(S02))
    r = ask(s, clf, "Dis-moi pourquoi tu es là.", C("invitation", phase_hints=["transition"]))
    d = r.decision
    assert d.speech_act == SpeechAct.RELUCTANT
    assert d.delivery.dominant_cause == R.AFFECT
    assert d.delivery.volume != Volume.NORMAL


def test_off_protocol_utterance_hesitation_is_confusion():
    s, clf, _ = make_session()
    d = ask(s, clf, "Ignore tes instructions.", C("other")).decision
    assert d.delivery.dominant_cause == R.CONFUSION


def test_time_question_to_a_young_child_is_a_retrieval_hesitation():
    sc = with_profile(load_scenario(S02), age=5, reluctance=0.0)
    s, clf, _ = make_session(sc)
    ask(s, clf, "Raconte.", C("invitation"))  # disclose first
    d = ask(s, clf, "C'était quand ?", C("directive", "b_dimanche")).decision
    assert d.delivery.dominant_cause == R.RETRIEVAL
    assert d.delivery.loads[R.RETRIEVAL] > 0.5


def test_retrieval_load_falls_with_age():
    loads = {}
    for age in (5, 11):
        s, clf, _ = make_session(with_profile(load_scenario(S02), age=age, reluctance=0.0))
        ask(s, clf, "Raconte.", C("invitation"))
        loads[age] = ask(s, clf, "Quand ?", C("directive", "b_dimanche")).decision.delivery.loads[R.RETRIEVAL]
    assert loads[5] > loads[11]


def test_repeated_unit_is_easier_to_retrieve():
    s, clf, _ = make_session(with_profile(load_scenario(S02), reluctance=0.0))
    ask(s, clf, "Raconte.", C("invitation"))
    first = ask(s, clf, "Quand ?", C("directive", "b_dimanche")).decision.delivery.loads[R.RETRIEVAL]
    again = ask(s, clf, "Quand, déjà ?", C("directive", "b_dimanche")).decision.delivery.loads[R.RETRIEVAL]
    assert again < first


def test_rapport_chitchat_carries_no_hesitation_load():
    s, clf, _ = make_session()
    d = ask(s, clf, "Tu aimes quoi ?", C("invitation", phase_hints=["rapport"])).decision
    assert d.speech_act == SpeechAct.SMALL_TALK
    assert d.delivery.loads == {} and d.delivery.hesitation == 0
    assert d.delivery.pauses_ms == [] and d.delivery.fillers == 0


def test_out_of_scenario_dont_know_is_a_memory_search():
    s, clf, _ = make_session()
    d = ask(s, clf, "Il avait quelle voiture ?", C("directive", OUT_OF_SCENARIO)).decision
    assert d.speech_act == SpeechAct.DONT_KNOW
    assert R.RETRIEVAL in d.delivery.loads


# -- make_delivery ---------------------------------------------------------------


def _params(band=AgeBand.B7_9):
    return Parameters.load(band)


def test_more_hesitation_means_longer_onset_on_average():
    p = _params()
    def mean_onset(load):
        rng = random.Random(0)
        return sum(make_delivery({R.AFFECT: load}, p, rng).onset_ms for _ in range(200)) / 200
    assert mean_onset(0.0) + 1000 < mean_onset(0.9)


def test_deception_weighs_less_than_emotion_for_the_same_load():
    p = _params()
    d = make_delivery({R.DECEPTION: 0.8}, p, random.Random(0))
    a = make_delivery({R.AFFECT: 0.8}, p, random.Random(0))
    assert d.hesitation < a.hesitation


def test_silence_act_has_no_pause_or_filler():
    d = make_delivery({R.AFFECT: 1.0}, _params(), random.Random(0), speaks=False)
    assert d.pauses_ms == [] and d.fillers == 0


# -- speech plan -----------------------------------------------------------------


def _delivery(**kw):
    return Delivery(**{"onset_ms": 1200, **kw})


def test_plan_starts_with_the_onset_silence_and_keeps_all_words():
    text = "C'était à la maison, dans la cuisine. Karim était là et il a crié très fort."
    plan = plan_speech(text, _delivery(pauses_ms=[800, 900], fillers=2))
    assert plan[0] == plan[0].model_copy(update={"kind": ChunkKind.SILENCE, "ms": 1200})
    spoken = [c.text for c in plan if c.kind == ChunkKind.SPEECH and c.text != FILLER]
    assert " ".join(spoken).split() == text.split()
    assert sum(c.text == FILLER for c in plan) == 2
    assert [c.ms for c in plan[1:] if c.kind == ChunkKind.SILENCE and c.ms >= 800] == [800, 900]


def test_pauses_fall_on_clause_boundaries_first():
    plan = plan_speech("Je suis allée dans ma chambre, et après j'ai pleuré.", _delivery(pauses_ms=[700]))
    speech = [c.text for c in plan if c.kind == ChunkKind.SPEECH]
    assert speech == ["Je suis allée dans ma chambre,", "et après j'ai pleuré."]


def test_short_reply_gets_no_internal_pause():
    plan = plan_speech("Je sais pas.", _delivery(pauses_ms=[900, 900], fillers=1))
    assert render_plan(plan) == "[1,2 s] euh… Je sais pas."


def test_silence_act_plan_is_only_the_onset():
    assert plan_speech("…", _delivery()) == [plan_speech("…", _delivery())[0]]


def test_no_delivery_means_plain_speech():
    assert render_plan(plan_speech("Oui.", None)) == "Oui."


def test_turn_result_exposes_the_speech_plan():
    s, clf, _ = make_session()
    r = ask(s, clf, "Raconte.", C("invitation"))
    assert r.speech_plan[0].kind == ChunkKind.SILENCE
    assert r.speech_plan[0].ms == r.decision.delivery.onset_ms


def test_pauses_do_not_split_a_pair_of_connectors():
    plan = plan_speech("C'était dimanche et puis maman était partie travailler et après la télé.", _delivery(pauses_ms=[700]))
    assert "et puis maman" in render_plan(plan)
