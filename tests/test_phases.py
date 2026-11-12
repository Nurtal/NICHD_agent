"""Phase tracking and neutral event (#6)."""

import pytest

from doubles import S01, C, ask, make_session
from nichd_sim.engine import SpeechAct
from nichd_sim.phases import Phase, ViolationKind
from nichd_sim.scenario import ScenarioError, load_scenario


def H(type, target=None, phase=None, **kw):
    return C(type, target, phase_hints=[phase] if phase else [], **kw)


def kinds(violations):
    return [(v.kind, v.phase) for v in violations]


def conforming_interview(s, clf):
    steps = [
        ("Bonjour Léo, je m'appelle Paul.", H("support", phase="rapport")),
        ("Qu'est-ce que tu aimes faire ?", H("invitation", phase="rapport")),
        ("Si tu ne sais pas, dis je ne sais pas.", H("ground_rule", phase="ground_rules")),
        ("Si je me trompe, corrige-moi.", H("ground_rule", phase="ground_rules")),
        ("Raconte-moi ton dernier anniversaire.", H("invitation", phase="narrative_practice")),
        ("Et ensuite ?", H("invitation", phase="narrative_practice")),
        ("Tu as parlé du gâteau, dis-m'en plus.", H("cued_invitation", "n_gateau", phase="narrative_practice")),
        ("Dis-moi pourquoi tu es venu me parler.", H("invitation", phase="transition")),
        ("Et après ?", H("invitation", phase="substantive")),
        ("Qui a poussé ?", H("directive", "d_pousse", phase="substantive")),
        ("Y a-t-il autre chose que je devrais savoir ?", H("invitation", phase="closure")),
        ("Merci Léo, tu vas faire quoi cet après-midi ?", H("support", phase="closure")),
    ]
    return [ask(s, clf, u, c) for u, c in steps]


def test_conforming_interview_has_no_violation_and_walks_through_all_phases():
    s, clf, _ = make_session()
    results = conforming_interview(s, clf)
    assert [r.phase for r in results] == [
        Phase.RAPPORT, Phase.RAPPORT, Phase.GROUND_RULES, Phase.GROUND_RULES,
        Phase.NARRATIVE_PRACTICE, Phase.NARRATIVE_PRACTICE, Phase.NARRATIVE_PRACTICE,
        Phase.SUBSTANTIVE,  # the child discloses at the transition prompt
        Phase.SUBSTANTIVE, Phase.SUBSTANTIVE, Phase.CLOSURE, Phase.CLOSURE,
    ]
    log = s.end()
    assert log.phase_violations == []
    assert [t.phase for t in log.turns][-1] == Phase.CLOSURE


def test_rapport_invitation_is_small_talk_without_scenario_facts():
    s, clf, _ = make_session()
    r = ask(s, clf, "Qu'est-ce que tu aimes faire ?", H("invitation", phase="rapport"))
    assert r.decision.speech_act == SpeechAct.SMALL_TALK and r.decision.allowed_units == []


def test_child_tells_the_neutral_event_during_narrative_practice():
    s, clf, _ = make_session()
    r = ask(s, clf, "Raconte-moi ton anniversaire.", H("invitation", phase="narrative_practice"))
    assert [u.id for u in r.decision.allowed_units] == ["n_anniversaire", "n_copains"]
    r = ask(s, clf, "Tu as parlé de tes copains, dis-m'en plus.", H("cued_invitation", "n_copains", phase="narrative_practice"))
    assert all(u.id.startswith("n_") for u in r.decision.allowed_units)
    r = ask(s, clf, "Hmm.", H("facilitator"))
    assert all(u.id.startswith("n_") for u in r.decision.allowed_units)
    assert not any(u.startswith(("b_", "d_", "a_")) for u in s.state.revealed)
    assert s.phase == Phase.NARRATIVE_PRACTICE  # the neutral event never counts as a disclosure


def test_directive_on_the_facts_before_the_transition_is_flagged():
    s, clf, _ = make_session()
    ask(s, clf, "Bonjour.", H("support", phase="rapport"))
    r = ask(s, clf, "Le monsieur, il a poussé qui ?", H("directive", "d_pousse"))
    assert (ViolationKind.PREMATURE_FOCUSED_QUESTION, Phase.RAPPORT) in kinds(r.violations)


def test_suggestive_question_on_the_facts_before_transition_is_flagged():
    s, clf, _ = make_session()
    r = ask(s, clf, "Il t'a fait peur le monsieur, hein ?", H("suggestive", "a_peur", suggested_proposition="il lui a fait peur"))
    assert ViolationKind.PREMATURE_FOCUSED_QUESTION in [v.kind for v in r.violations]


def test_focused_question_about_the_neutral_event_is_not_a_violation():
    s, clf, _ = make_session()
    r = ask(s, clf, "C'était quoi ton gâteau ?", H("directive", "n_gateau", phase="narrative_practice"))
    assert ViolationKind.PREMATURE_FOCUSED_QUESTION not in [v.kind for v in r.violations]


def test_skipped_phases_are_flagged():
    s, clf, _ = make_session()
    ask(s, clf, "Bonjour.", H("support", phase="rapport"))
    ask(s, clf, "Comment ça va ?", H("support", phase="rapport"))
    r = ask(s, clf, "Dis-moi pourquoi tu es là.", H("invitation", phase="transition"))
    skipped = [v.phase for v in r.violations if v.kind == ViolationKind.SKIPPED_PHASE]
    assert skipped == [Phase.GROUND_RULES, Phase.NARRATIVE_PRACTICE]


def test_truncated_phase_is_flagged():
    s, clf, _ = make_session()
    ask(s, clf, "Bonjour.", H("support", phase="rapport"))
    ask(s, clf, "Ça va ?", H("support", phase="rapport"))
    ask(s, clf, "Dis je sais pas si tu sais pas.", H("ground_rule", phase="ground_rules"))  # only one rule
    r = ask(s, clf, "Raconte ton anniversaire.", H("invitation", phase="narrative_practice"))
    assert (ViolationKind.TRUNCATED_PHASE, Phase.GROUND_RULES) in kinds(r.violations)


def test_missing_closure_is_flagged_at_end():
    s, clf, _ = make_session()
    ask(s, clf, "Raconte.", H("invitation", phase="substantive"))
    log = s.end()
    assert (ViolationKind.MISSING_CLOSURE, Phase.CLOSURE) in kinds(log.phase_violations)
    assert log.phase_violations[-1].turn is None


def test_phases_never_go_backwards():
    s, clf, _ = make_session()
    conforming_interview(s, clf)
    r = ask(s, clf, "Tu m'aides beaucoup.", H("support", phase="rapport"))
    assert r.phase == Phase.CLOSURE


def test_without_hints_ground_rules_and_disclosure_still_drive_the_phase():
    s, clf, _ = make_session()
    assert ask(s, clf, "Bonjour.", C("support")).phase == Phase.RAPPORT
    assert ask(s, clf, "Tu peux dire je sais pas.", C("ground_rule")).phase == Phase.GROUND_RULES
    assert ask(s, clf, "Raconte-moi.", C("invitation")).phase == Phase.SUBSTANTIVE


def test_manual_tag_carries_the_phase():
    from nichd_sim.classification import ClassificationContext
    from nichd_sim.classifiers.manual import ManualClassificationError, ManualClassifier

    ctx = ClassificationContext(scenario=load_scenario(S01))
    c = ManualClassifier().classify("[inv@pratique] Raconte ton anniversaire.", ctx)
    assert c.phase_hints == ["narrative_practice"] and c.clean_text == "Raconte ton anniversaire."
    c = ManualClassifier().classify("[ind@faits:d_pousse] Dis-m'en plus.", ctx)
    assert c.phase_hints == ["substantive"] and c.target == "d_pousse"
    with pytest.raises(ManualClassificationError):
        ManualClassifier().classify("[inv@nulle] x", ctx)


def test_phase_is_logged_per_turn():
    s, clf, _ = make_session()
    conforming_interview(s, clf)
    data = s.end().model_dump()
    assert data["turns"][4]["phase"] == "narrative_practice"
    assert data["phase_violations"] == []


def test_scenario_unit_ids_must_be_unique_across_events(tmp_path):
    import yaml

    data = yaml.safe_load(S01.read_text())
    data["neutral_event"]["segments"][0]["units"][0]["id"] = "b_mamie"
    bad = tmp_path / "dup.yaml"
    bad.write_text(yaml.safe_dump(data, allow_unicode=True))
    with pytest.raises(ScenarioError, match="dupliqué"):
        load_scenario(bad)
