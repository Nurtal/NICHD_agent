"""Training scenarios #2 and #3 (#13), plus checks shared by every scenario sheet."""

from pathlib import Path

import pytest

from doubles import ROOT, C, ask, make_session
from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.engine import SpeechAct
from nichd_sim.phases import Phase
from nichd_sim.realization import TemplateRealizer
from nichd_sim.scenario import ValidationStatus, load_scenario
from nichd_sim.scenario_check import Level, check_scenario

SCENARIOS = sorted((ROOT / "scenarios").glob("*.yaml"))
S02 = ROOT / "scenarios" / "s02_violences_maison.yaml"
S03 = ROOT / "scenarios" / "s03_vol_boulangerie.yaml"


def H(type, target=None, phase=None, **kw):
    return C(type, target, phase_hints=[phase] if phase else [], **kw)


def test_there_are_at_least_three_scenarios_with_unique_ids():
    ids = [load_scenario(p).id for p in SCENARIOS]
    assert len(ids) >= 3 and len(set(ids)) == len(ids)


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenario_passes_authoring_checks_and_awaits_trainer_validation(path: Path):
    sc = load_scenario(path)
    assert sc.status == ValidationStatus.DRAFT
    findings = [f for f in check_scenario(sc) if f.level != Level.INFO]
    assert findings == [], "\n".join(map(str, findings))


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


# -- lot 2 (#30) -----------------------------------------------------------------

LOT2 = {p.stem: p for p in SCENARIOS if p.name[:3] in ("s04", "s05", "s06", "s07")}


def prompts_until_disclosure(path, max_prompts=8):
    s, clf, _ = make_session(load_scenario(path))
    for i in range(1, max_prompts + 1):
        r = ask(s, clf, f"Dis-moi pourquoi tu es là {i}.", H("invitation", phase="transition"))
        if r.decision.speech_act == SpeechAct.ANSWER:
            return i
    return None


def test_lot2_is_present():
    assert sorted(LOT2) == ["s04_violences_conjugales", "s05_negligence", "s06_racket", "s07_delit_fuite"]


def test_lot2_disclosure_matches_each_profile():
    assert prompts_until_disclosure(LOT2["s07_delit_fuite"]) == 1  # very cooperative
    assert prompts_until_disclosure(LOT2["s05_negligence"]) == 2
    assert prompts_until_disclosure(LOT2["s06_racket"]) == 3  # embarrassed
    assert prompts_until_disclosure(LOT2["s04_violences_conjugales"]) == 3  # reluctant young witness


def test_lot2_repeated_events_have_a_frequency_unit():
    for stem in ("s04_violences_conjugales", "s05_negligence", "s06_racket"):
        cats = {u.category for _, u in load_scenario(LOT2[stem]).target_units()}
        assert "frequency" in cats, stem


def test_young_suggestible_witness_acquiesces_far_more_than_the_teenager():
    def rate(path):
        base = load_scenario(path)
        hits = 0
        for seed in range(300):
            s, clf, _ = make_session(base, seed=seed)
            for i in range(4):
                ask(s, clf, f"Raconte {i}.", H("invitation", phase="transition"))
            r = ask(s, clf, "Il avait un couteau, hein ?", H("suggestive", OUT_OF_SCENARIO, phase="substantive", suggested_proposition="il avait un couteau"))
            hits += r.decision.speech_act == SpeechAct.ACQUIESCE
        return hits / 300

    assert rate(LOT2["s04_violences_conjugales"]) > 3 * rate(LOT2["s07_delit_fuite"])
