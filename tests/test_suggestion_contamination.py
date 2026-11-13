"""Suggestion, option-posing and persistent contamination (#5)."""

from doubles import S01, C, ask, make_session, with_profile
from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.engine import SpeechAct
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import AgeBand, load_scenario

FORCE = {"suggestibility_multiplier_range": [1, 1]}  # neutralize profile modulation


def scenario(**overrides):
    sc = load_scenario(S01)
    return sc.model_copy(update={"parameter_overrides": {**FORCE, **overrides}})


def ids(r):
    return [u.id for u in r.decision.allowed_units]


# -- option-posing ----------------------------------------------------------


def test_forced_choice_recency_bias_creates_a_contaminated_unit():
    s, clf, _ = make_session(scenario(p_recency=1, p_integration=0))
    r = ask(s, clf, "C'était le matin ou l'après-midi ?", C("option_posing", "b_quand", options=["le matin", "l'après-midi"]))
    assert r.decision.speech_act == SpeechAct.ACQUIESCE
    assert r.decision.allowed_units[0].value == "l'après-midi" and r.decision.allowed_units[0].contaminated
    [cu] = s.state.contaminated
    assert cu.value == "l'après-midi" and cu.source_turn == 1 and cu.source_type == "option_posing"
    assert s.state.revealed == []


def test_forced_choice_with_correct_option_can_be_answered_correctly():
    s, clf, _ = make_session(scenario(p_correct_option=1))
    r = ask(s, clf, "Il a poussé ou il a tapé ?", C("option_posing", "d_pousse", options=["il a poussé", "il a tapé"]))
    assert r.decision.speech_act == SpeechAct.ANSWER and ids(r) == ["d_pousse"]
    assert r.decision.lucky_suggestion and s.state.contaminated == []


def test_forced_choice_wrong_answer_despite_correct_option():
    s, clf, _ = make_session(scenario(p_correct_option=0, p_recency=0))
    r = ask(s, clf, "Il a poussé ou il a tapé ?", C("option_posing", "d_pousse", options=["il a poussé", "il a tapé"]))
    assert r.decision.speech_act == SpeechAct.ACQUIESCE
    assert r.decision.allowed_units[0].value == "il a tapé"


def test_forced_choice_without_correct_option_may_get_dont_know():
    s, clf, _ = make_session(scenario(p_recency=0))
    r = ask(s, clf, "Il était grand ou petit ?", C("option_posing", OUT_OF_SCENARIO, options=["grand", "petit"]))
    assert r.decision.speech_act == SpeechAct.DONT_KNOW and s.state.contaminated == []


def test_yes_no_true_proposition_reveals_the_unit():
    s, clf, _ = make_session(scenario())
    r = ask(s, clf, "Il y avait un chien ?", C("option_posing", "d_chien", suggested_proposition="il y avait un chien"))
    assert r.decision.speech_act == SpeechAct.ANSWER and ids(r) == ["d_chien"]


def test_yes_no_false_proposition_yes_bias_or_denial():
    s, clf, _ = make_session(scenario(p_yes_bias=1, p_integration=0))
    r = ask(s, clf, "Il y avait un vélo ?", C("option_posing", OUT_OF_SCENARIO, suggested_proposition="il y avait un vélo"))
    assert r.decision.speech_act == SpeechAct.ACQUIESCE and r.decision.new_contamination == "c1"
    s, clf, _ = make_session(scenario(p_yes_bias=0))
    r = ask(s, clf, "Il y avait un vélo ?", C("option_posing", OUT_OF_SCENARIO, suggested_proposition="il y avait un vélo"))
    assert r.decision.speech_act == SpeechAct.DENY and s.state.contaminated == []


# -- suggestive -------------------------------------------------------------


def test_false_suggestion_acquiesced_and_integrated_resurfaces_at_a_later_invitation():
    s, clf, _ = make_session(scenario(p_acquiesce=1, p_integration=1, p_contamination_recall=1))
    r = ask(s, clf, "Il l'a frappé avec un bâton, hein ?", C("suggestive", "d_pousse", suggested_proposition="il l'a frappé avec un bâton"))
    assert r.decision.speech_act == SpeechAct.ACQUIESCE
    assert r.decision.new_contamination == "c1"
    [cu] = s.state.contaminated
    assert cu.integrated and cu.source_turn == 1 and cu.target == "d_pousse"
    r = ask(s, clf, "Dis-moi tout.", C("invitation"))
    resurfaced = [u for u in r.decision.allowed_units if u.contaminated]
    assert [u.value for u in resurfaced] == ["il l'a frappé avec un bâton"]
    assert "c1" not in s.state.revealed


def test_acquiesced_but_not_integrated_detail_does_not_resurface():
    s, clf, _ = make_session(scenario(p_acquiesce=1, p_integration=0, p_contamination_recall=1))
    ask(s, clf, "Il avait un couteau, hein ?", C("suggestive", OUT_OF_SCENARIO, suggested_proposition="il avait un couteau"))
    for i in range(4):
        r = ask(s, clf, f"Raconte {i}.", C("invitation"))
        assert not any(u.contaminated for u in r.decision.allowed_units)
    assert len(s.state.contaminated) == 1


def test_lucky_suggestion_reveals_truth_without_contamination_but_is_flagged():
    s, clf, _ = make_session(scenario(p_acquiesce=1))
    r = ask(s, clf, "Il l'a poussé, c'est ça ?", C("suggestive", "d_pousse", suggested_proposition="il l'a poussé"))
    assert r.decision.speech_act == SpeechAct.ACQUIESCE and ids(r) == ["d_pousse"]
    assert r.decision.lucky_suggestion and s.state.contaminated == []
    assert s.state.revealed == ["d_pousse"]


def test_false_suggestion_resisted():
    s, clf, _ = make_session(scenario(p_acquiesce=0))
    r = ask(s, clf, "Il avait un couteau, hein ?", C("suggestive", OUT_OF_SCENARIO, suggested_proposition="il avait un couteau"))
    assert r.decision.speech_act == SpeechAct.DENY and s.state.contaminated == []


def test_younger_children_acquiesce_more_than_older_ones():
    base = load_scenario(S01)

    def rate(age):
        hits = 0
        sc = with_profile(base, age=age, suggestibility=0.5)
        for seed in range(300):
            s, clf, _ = make_session(sc, seed=seed)
            r = ask(s, clf, "Il avait un couteau, hein ?", C("suggestive", OUT_OF_SCENARIO, suggested_proposition="il avait un couteau"))
            hits += r.decision.speech_act == SpeechAct.ACQUIESCE
        return hits / 300

    r5, r8, r11 = rate(5), rate(8), rate(11)
    assert r5 > r8 > r11
    from nichd_sim.parameters import Parameters
    from nichd_sim.scenario import AgeBand

    expected = Parameters.load(AgeBand.B4_6)["p_acquiesce"]
    assert abs(r5 - expected) < 0.08  # p_acquiesce(4_6) with neutral suggestibility


def test_suggestibility_profile_modulates_acquiescence():
    base = load_scenario(S01)

    def rate(sugg):
        hits = 0
        sc = with_profile(base, suggestibility=sugg)
        for seed in range(300):
            s, clf, _ = make_session(sc, seed=seed)
            r = ask(s, clf, "Il avait un couteau, hein ?", C("suggestive", OUT_OF_SCENARIO, suggested_proposition="il avait un couteau"))
            hits += r.decision.speech_act == SpeechAct.ACQUIESCE
        return hits / 300

    assert rate(0.9) > rate(0.1) + 0.2


# -- confabulation & compound -----------------------------------------------


def test_out_of_scenario_directive_can_be_confabulated_and_is_recorded():
    s, clf, _ = make_session(scenario(p_confabulation=1))
    r = ask(s, clf, "Il avait quelle voiture ?", C("directive", OUT_OF_SCENARIO))
    assert r.decision.speech_act == SpeechAct.CONFABULATE
    [cu] = s.state.contaminated
    assert cu.value == r.response and cu.source_type == "directive" and not cu.integrated


def test_compound_question_follows_its_most_directive_element():
    s, clf, _ = make_session(scenario(p_acquiesce=1, p_integration=0))
    r = ask(
        s, clf, "Raconte-moi, il avait un couteau ?",
        C("compound", OUT_OF_SCENARIO, inner_type="suggestive", suggested_proposition="il avait un couteau"),
    )
    assert r.decision.effective_type == "suggestive" and r.decision.speech_act == SpeechAct.ACQUIESCE
    assert s.state.contaminated[0].source_type == "compound"
    r = ask(s, clf, "Il était où et il a fait quoi ?", C("compound", "d_pousse"))
    assert r.decision.effective_type == "directive" and ids(r) == ["d_pousse"]


# -- determinism, parameters, log -------------------------------------------


def test_same_seed_and_script_give_identical_decisions():
    script = [
        ("a", C("suggestive", "d_pousse", suggested_proposition="il l'a tapé")),
        ("b", C("option_posing", "b_quand", options=["le matin", "le soir"])),
        ("c", C("directive", OUT_OF_SCENARIO)),
        ("d", C("invitation")),
    ]
    runs = []
    for _ in range(2):
        s, clf, _ = make_session(seed=123)
        runs.append([ask(s, clf, u, c).decision for u, c in script])
    assert runs[0] == runs[1]


def test_every_parameter_has_a_source_and_overrides_apply():
    params = Parameters.load(AgeBand.B4_6)
    for name, p in params.table.items():
        assert p.source.strip(), name
        assert isinstance(p.estimated, bool)
    assert Parameters.load(AgeBand.B4_6, {"p_acquiesce": 0.9})["p_acquiesce"] == 0.9
    assert Parameters.load(AgeBand.B7_9, {"p_acquiesce": {"7_9": 0.1}})["p_acquiesce"] == 0.1
    assert Parameters.load(AgeBand.B4_6, {"p_acquiesce": {"7_9": 0.1}})["p_acquiesce"] == params["p_acquiesce"]


def test_unknown_parameter_override_is_rejected():
    import pytest

    from nichd_sim.parameters import ParameterError

    with pytest.raises(ParameterError):
        Parameters.load(AgeBand.B4_6, {"p_inconnu": 1})


def test_log_exposes_contaminations_with_their_origin():
    s, clf, _ = make_session(scenario(p_acquiesce=1, p_integration=1))
    ask(s, clf, "Raconte.", C("invitation"))
    ask(s, clf, "Il avait un couteau, hein ?", C("suggestive", OUT_OF_SCENARIO, suggested_proposition="il avait un couteau"))
    log = s.log.model_dump()
    cont = log["turns"][-1]["state_after"]["contaminated"]
    assert cont == [
        {"id": "c1", "value": "il avait un couteau", "target": OUT_OF_SCENARIO, "source_turn": 2,
         "source_type": "suggestive", "integrated": True, "times_said": 1}
    ]
