"""Training scenarios #2 and #3 (#13), plus checks shared by every scenario sheet."""

from pathlib import Path

import pytest

from doubles import ROOT, C, ask, make_session
from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.engine import SpeechAct
from nichd_sim.phases import Phase
from nichd_sim.realization import TemplateRealizer
from nichd_sim.scenario import Centrality, ValidationStatus, load_scenario
from nichd_sim.text import normalize

SCENARIOS = sorted((ROOT / "scenarios").glob("*.yaml"))
S02 = ROOT / "scenarios" / "s02_violences_maison.yaml"
S03 = ROOT / "scenarios" / "s03_vol_boulangerie.yaml"
FORBIDDEN_ANCHORS = {"deja", "maison", "ecole", "pris", "appele", "car", "soir", "partie", "sortie"}


def H(type, target=None, phase=None, **kw):
    return C(type, target, phase_hints=[phase] if phase else [], **kw)


def test_there_are_three_scenarios():
    assert [p.name[:3] for p in SCENARIOS] == ["s01", "s02", "s03"]


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenario_is_complete_and_awaits_trainer_validation(path: Path):
    sc = load_scenario(path)
    assert sc.status == ValidationStatus.DRAFT
    assert sc.neutral_event is not None
    target = [u for _, u in sc.target_units()]
    assert sum(u.centrality == Centrality.CENTRAL for u in target) >= 6
    assert {u.category for u in target} >= {"who", "what", "where", "when"}
    # every unit is expressed by at least one of its anchors (needed by the omission check)
    for _, u in sc.all_units():
        assert any(normalize(a) in normalize(u.value) for a in u.anchors), u.id
        assert not {normalize(a) for a in u.anchors} & FORBIDDEN_ANCHORS, u.id


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenario_is_playable_end_to_end(path: Path):
    sc = load_scenario(path)
    s, clf, _ = make_session(sc)
    s.realizer = TemplateRealizer()
    for i in range(6):
        ask(s, clf, f"Dis-moi pourquoi tu es là {i}.", H("invitation", phase="transition"))
    for i in range(10):
        ask(s, clf, f"Et après {i} ?", H("invitation", phase="substantive"))
    log = s.end()
    assert log.feedback.metrics.accurate_info_recall.revealed > 0
    assert not any(t.fallback_used for t in log.turns)  # authored values pass the filter


def test_s02_needs_several_transition_prompts_with_default_parameters():
    s, clf, _ = make_session(load_scenario(S02))
    acts = [ask(s, clf, f"Dis-moi pourquoi tu es venue {i}.", H("invitation", phase="transition")).decision.speech_act for i in range(5)]
    first_answer = acts.index(SpeechAct.ANSWER)
    assert first_answer >= 2 and all(a == SpeechAct.RELUCTANT for a in acts[:first_answer])
    assert s.phase == Phase.SUBSTANTIVE


def test_s03_acquiesces_much_less_than_s01():
    def rate(path):
        base = load_scenario(path)
        hits = 0
        for seed in range(300):
            s, clf, _ = make_session(base, seed=seed)
            ask(s, clf, "Raconte.", H("invitation", phase="transition"))
            r = ask(s, clf, "Il y avait un chien, hein ?", H("suggestive", OUT_OF_SCENARIO, phase="substantive", suggested_proposition="il y avait un chien"))
            hits += r.decision.speech_act == SpeechAct.ACQUIESCE
        return hits / 300

    s01, s03 = rate(ROOT / "scenarios" / "s01_bagarre_parc.yaml"), rate(S03)
    assert s01 > 2 * s03
