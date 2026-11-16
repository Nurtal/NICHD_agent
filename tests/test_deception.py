"""Deception (ADR 0002): protected facts, omissions, lies, retraction, metrics, filter."""

from pathlib import Path

import pytest
import yaml
from doubles import C, ScriptedClassifier, ask, make_session

from nichd_sim.delivery import HesitationCause
from nichd_sim.engine import LieKind, SpeechAct
from nichd_sim.output_filter import OutputFilter
from nichd_sim.realization import Realization, TemplateRealizer, build_system_prompt
from nichd_sim.replay import find_scenario, replay
from nichd_sim.scenario import Scenario, ScenarioError, load_scenario
from nichd_sim.session import Session

ROOT = Path(__file__).resolve().parent.parent
S08 = ROOT / "scenarios" / "s08_violences_maison_secret.yaml"
PROTECTED = ["d_karim", "d_crie", "d_bras", "d_tape", "d_frequence", "a_secret"]


def s08(strength=None, **profile) -> Scenario:
    sc = load_scenario(S08)
    if strength is not None:
        sc = sc.model_copy(update={"deception": sc.deception.model_copy(update={"strength": strength})})
    if profile:
        sc = sc.model_copy(update={"child_profile": sc.child_profile.model_copy(update=profile)})
    return sc


def open_session(strength=1.0, seed=0):
    """A disclosed, non-reluctant child who protects the facts with the given strength."""
    s, clf, real = make_session(s08(strength, reluctance=0.0), seed=seed)
    return s, clf, real


def ids(r):
    return [u.id for u in r.decision.allowed_units]


# -- scenario ------------------------------------------------------------------


def _raw():
    return yaml.safe_load(S08.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d["deception"]["protected"].append("n_piscine"), "pas une unité de l'événement cible"),
        (lambda d: d["deception"]["cover_stories"][0]["covers"].append("b_jus"), "n'est pas un fait protégé"),
        (lambda d: d["deception"]["minimizations"][0]["covers"].append("d_bras"), "exactement un fait protégé"),
        (lambda d: d["deception"]["cover_stories"][0].update(id="b_jus"), "dupliqué"),
    ],
)
def test_invalid_deception_blocks_are_rejected(tmp_path, mutate, message):
    raw = _raw()
    mutate(raw)
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ScenarioError, match=message):
        load_scenario(path)


def test_scenario_without_deception_never_lies():
    s, clf, _ = make_session(load_scenario(ROOT / "scenarios" / "s02_violences_maison.yaml").model_copy(
        update={"child_profile": load_scenario(S08).child_profile.model_copy(update={"reluctance": 0.0})}))
    assert s.state.concealment == 0
    for i in range(8):
        r = ask(s, clf, f"u{i}", C("invitation"))
        assert r.decision.lie is None and r.decision.withheld == []
    assert s.state.lies == []


# -- omission ----------------------------------------------------------------------


def test_full_concealment_omits_every_protected_fact_from_narratives():
    s, clf, _ = open_session(strength=1.0)
    said, withheld = [], set()
    for i in range(10):
        r = ask(s, clf, f"Raconte {i}", C("invitation"))
        said += ids(r)
        withheld |= set(r.decision.withheld)
    assert not set(said) & set(PROTECTED) - {"l_escalier"}
    assert withheld == set(PROTECTED)
    omissions = [lr for lr in s.state.lies if lr.kind == LieKind.OMISSION]
    assert sorted(lr.protected for lr in omissions) == sorted(PROTECTED)  # one record per fact


def test_narrative_offers_the_cover_story_once_nothing_else_is_left():
    s, clf, _ = open_session(strength=1.0)
    acts = [ask(s, clf, f"Raconte {i}", C("invitation")).decision for i in range(10)]
    covers = [d for d in acts if d.lie is not None and d.lie.kind == LieKind.COVER_STORY]
    assert len(covers) == 1
    assert [u.id for u in covers[0].allowed_units] == ["l_escalier"]
    assert covers[0].allowed_units[0].lie


def test_no_concealment_tells_everything():
    s, clf, _ = open_session(strength=0.0)
    said = []
    for i in range(10):
        said += ids(ask(s, clf, f"Raconte {i}", C("invitation")))
    assert set(PROTECTED) <= set(said)
    assert s.state.lies == []


def test_facts_come_out_in_the_authored_order():
    """A fact can be visible only if every less-guarded fact (earlier in the list) is visible."""
    for seed in range(20):
        s, _, _ = open_session(strength=1.0, seed=seed)
        engine = s.engine
        for level in [i / 20 for i in range(21)]:
            engine.state.concealment = level
            hidden = [engine._lies_about(engine.scenario.unit(u)) for u in PROTECTED]
            assert hidden == sorted(hidden), (seed, level, hidden)


# -- lies to focused questions --------------------------------------------------------


def test_directive_on_a_protected_fact_without_lie_content_is_feigned_ignorance():
    s, clf, _ = open_session()
    r = ask(s, clf, "Qui était là ?", C("directive", "d_karim"))
    assert r.decision.speech_act == SpeechAct.DONT_KNOW
    assert r.decision.lie.kind == LieKind.FEIGNED_IGNORANCE
    assert r.decision.lie.protected == "d_karim"
    assert "d_karim" not in s.state.revealed


def test_a_lie_is_kept_consistently():
    s, clf, _ = open_session()
    first = ask(s, clf, "Qui était là ?", C("directive", "d_karim")).decision.lie
    again = ask(s, clf, "Qui était avec toi ?", C("directive", "d_karim")).decision.lie
    assert again.id == first.id and again.times == 2
    assert len([lr for lr in s.state.lies if lr.kind != LieKind.OMISSION]) == 1


def test_true_suggestion_is_minimized_when_the_author_wrote_a_minimization():
    s, clf, _ = open_session()
    r = ask(s, clf, "Il t'a tapé, hein ?", C("suggestive", "d_tape", suggested_proposition="il t'a tapé"))
    assert r.decision.lie.kind == LieKind.MINIMIZATION
    assert ids(r) == ["l_pousse"]
    assert not r.decision.lucky_suggestion


def test_true_yes_no_question_gets_the_cover_story():
    s, clf, _ = open_session()
    r = ask(s, clf, "Il t'a attrapé le bras ?", C("option_posing", "d_bras", suggested_proposition="attrapé le bras"))
    assert r.decision.lie.kind == LieKind.COVER_STORY
    assert ids(r) == ["l_escalier"]


def test_true_suggestion_without_lie_content_is_denied():
    s, clf, _ = open_session()
    r = ask(s, clf, "C'était Karim, hein ?", C("suggestive", "d_karim", suggested_proposition="Karim"))
    assert r.decision.speech_act == SpeechAct.DENY
    assert r.decision.lie.kind == LieKind.FALSE_DENY


def test_cover_story_is_dropped_once_a_covered_fact_is_out():
    s, clf, _ = open_session(strength=0.0)
    ask(s, clf, "Raconte.", C("directive", "d_bras"))  # told truthfully
    s.engine.state.concealment = 1.0
    r = ask(s, clf, "Il t'a tapé dans le dos ?", C("option_posing", "d_tape", suggested_proposition="tapé"))
    assert r.decision.lie.kind == LieKind.MINIMIZATION  # not the staircase story


def test_lie_content_is_never_counted_as_revealed():
    s, clf, _ = open_session()
    ask(s, clf, "Il t'a attrapé le bras ?", C("option_posing", "d_bras", suggested_proposition="attrapé le bras"))
    assert "l_escalier" not in s.state.revealed
    m = s.end().feedback.metrics
    assert all(e.id != "l_escalier" for e in m.accurate_info_recall.elicited)


# -- concealment dynamics and retraction ---------------------------------------------


def test_support_lowers_and_pressure_raises_concealment():
    s, clf, _ = open_session(strength=0.5)
    ask(s, clf, "Tu peux tout me dire.", C("support"))
    assert s.state.concealment == pytest.approx(0.4)
    ask(s, clf, "Il t'a tapé, hein ?", C("suggestive", "d_tape", suggested_proposition="tapé"))
    assert s.state.concealment == pytest.approx(0.48)


def test_support_leads_to_retraction_and_then_to_the_truth():
    s, clf, _ = open_session(strength=0.6)
    lie = ask(s, clf, "Il t'a attrapé le bras ?", C("option_posing", "d_bras", suggested_proposition="bras")).decision.lie
    assert lie.kind == LieKind.COVER_STORY
    retraction = None
    for i in range(12):
        r = ask(s, clf, f"Je suis là pour t'écouter {i}", C("support"))
        if r.decision.speech_act == SpeechAct.RETRACT:
            retraction = r.decision
            break
    assert retraction is not None, "l'enfant n'est jamais revenu sur son mensonge"
    assert retraction.retraction.id == lie.id
    assert {u.id for u in retraction.allowed_units} == {"d_bras", "d_tape"}  # what the cover story hid
    assert all(not u.lie for u in retraction.allowed_units)
    record = next(lr for lr in s.state.lies if lr.id == lie.id)
    assert record.retracted_turn == s.state.turn
    r = ask(s, clf, "Comment tu t'es fait ce bleu ?", C("directive", "d_bras"))
    assert r.decision.lie is None and ids(r) == ["d_bras"]


def test_no_retraction_while_concealment_is_high():
    s, clf, _ = open_session(strength=1.0)
    ask(s, clf, "Qui était là ?", C("directive", "d_karim"))
    for i in range(5):
        r = ask(s, clf, f"Raconte {i}", C("invitation"))
        assert r.decision.speech_act != SpeechAct.RETRACT


# -- delivery ---------------------------------------------------------------------------


def test_lying_adds_a_deception_load_that_is_lower_once_rehearsed():
    s, clf, _ = open_session()
    first = ask(s, clf, "Il t'a attrapé le bras ?", C("option_posing", "d_bras", suggested_proposition="bras"))
    again = ask(s, clf, "Tu t'es fait comment ce bleu ?", C("directive", "d_bras"))
    a, b = first.decision.delivery.loads, again.decision.delivery.loads
    assert a[HesitationCause.DECEPTION] > b[HesitationCause.DECEPTION] > 0


def test_cover_story_costs_more_than_a_plain_denial():
    s, clf, _ = open_session()
    deny = ask(s, clf, "C'était Karim ?", C("suggestive", "d_karim", suggested_proposition="Karim")).decision
    cover = ask(s, clf, "Il t'a attrapé ?", C("option_posing", "d_bras", suggested_proposition="bras")).decision
    assert cover.delivery.loads[HesitationCause.DECEPTION] > deny.delivery.loads[HesitationCause.DECEPTION]


def test_hesitation_is_not_a_lie_detector():
    """Truthful answers about hard or painful facts also hesitate, sometimes more than a lie."""
    s, clf, _ = make_session(s08(0.0, reluctance=0.6, age=5))
    for i in range(3):
        ask(s, clf, f"Raconte {i}", C("invitation", phase_hints=["transition"]))
    truthful = ask(s, clf, "C'était quand ?", C("directive", "b_dimanche")).decision.delivery
    l, cl, _ = open_session(strength=1.0)
    lie = ask(l, cl, "Qui était là ?", C("directive", "d_karim")).decision.delivery
    assert truthful.hesitation > lie.hesitation


# -- realization, filter, metrics, replay ------------------------------------------------


def test_retraction_prompt_names_the_lie_and_lists_the_truth():
    s, clf, _ = open_session(strength=0.6)
    ask(s, clf, "Il t'a attrapé le bras ?", C("option_posing", "d_bras", suggested_proposition="bras"))
    for i in range(12):
        r = ask(s, clf, f"Courage {i}", C("support"))
        if r.decision.speech_act == SpeechAct.RETRACT:
            break
    prompt = build_system_prompt(r.decision, s.scenario.child_profile)
    assert "je suis tombée dans l'escalier" in prompt
    assert "il m'a attrapé le bras très fort" in prompt


def test_filter_treats_lie_content_like_units():
    sc = load_scenario(S08)
    f = OutputFilter(sc)
    s, clf, _ = open_session()
    d = ask(s, clf, "Raconte.", C("directive", "b_cuisine")).decision
    assert f.check("C'était dans la cuisine, je suis tombée dans l'escalier.", d).leaked_units == ["l_escalier"]
    assert f.check("C'était dans la cuisine, je suis tombée dans l'escalier.", d, known_unit_ids=["l_escalier"]).ok
    lie = ask(s, clf, "Il t'a attrapé ?", C("option_posing", "d_bras", suggested_proposition="bras")).decision
    assert f.check("Non, rien du tout.", lie).missing_units == ["l_escalier"]
    assert f.check("Je suis tombée dans l'escalier.", lie).ok


class _SaysCoverStoryRealizer:
    """Realizes every decision faithfully, but also repeats the cover story."""

    def realize(self, decision, profile, history, attempt=0):
        text = TemplateRealizer().realize(decision, profile, history).text
        return Realization(text=f"{text} Je suis tombée dans l'escalier.")


def test_session_lets_the_child_repeat_its_own_lie():
    clf = ScriptedClassifier()
    s = Session(s08(1.0, reluctance=0.0), clf, _SaysCoverStoryRealizer())
    r = ask(s, clf, "Où ?", C("directive", "b_cuisine"))
    assert r.fallback_used  # cover story never told yet: a leak
    ask(s, clf, "Il t'a attrapé ?", C("option_posing", "d_bras", suggested_proposition="bras"))
    r = ask(s, clf, "Où, déjà ?", C("directive", "b_cuisine"))
    assert not r.fallback_used  # the child may repeat its own lie


def test_metrics_summarize_lies_retractions_and_obtained_facts():
    s, clf, _ = open_session(strength=0.6)
    ask(s, clf, "Il t'a attrapé le bras ?", C("option_posing", "d_bras", suggested_proposition="bras"))
    ask(s, clf, "Qui était là ?", C("directive", "d_karim"))
    for i in range(12):
        if ask(s, clf, f"Courage {i}", C("support")).decision.speech_act == SpeechAct.RETRACT:
            break
    m = s.end().feedback.metrics.deception
    assert m.protected_total == 6
    assert {e.kind for e in m.lies} >= {"cover_story"}
    assert m.retracted >= 1 and m.retracted + m.standing == len(m.lies)
    assert "d_bras" in [e.id for e in m.protected_obtained]
    assert m.lies_by_question_type["option_posing"] == 1
    assert m.lies[0].utterance == "Il t'a attrapé le bras ?"


def test_metrics_have_no_deception_section_without_deception():
    s, clf, _ = make_session()
    ask(s, clf, "Raconte.", C("invitation"))
    assert s.end().feedback.metrics.deception is None


def test_s08_session_replays_identically(monkeypatch):
    monkeypatch.chdir(ROOT)
    s, clf, _ = make_session(load_scenario(S08), seed=5)
    script = [C("support"), C("invitation", phase_hints=["transition"]), C("invitation"), C("invitation"),
              C("directive", "d_karim"), C("option_posing", "d_bras", suggested_proposition="bras"),
              C("support"), C("support"), C("support"), C("invitation"), C("invitation")]
    for i, c in enumerate(script):
        ask(s, clf, f"u{i}", c)
    log = s.end()
    assert replay(log, find_scenario(log)).identical
