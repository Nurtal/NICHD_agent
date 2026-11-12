"""Effects of preparatory phases on the child, disclosure threshold, closure (#9)."""

from doubles import S01, C, ask, make_session, with_profile
from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.engine import SpeechAct
from nichd_sim.phases import Phase, ViolationKind
from nichd_sim.scenario import load_scenario
from nichd_sim.session import SOFT_TURN_LIMIT


def H(type, target=None, phase=None, **kw):
    return C(type, target, phase_hints=[phase] if phase else [], **kw)


def child(reluctance=0.2, suggestibility=0.5, verbal_skills=0.4, **overrides):
    sc = with_profile(load_scenario(S01), reluctance=reluctance, suggestibility=suggestibility, verbal_skills=verbal_skills)
    if overrides:
        sc = sc.model_copy(update={"parameter_overrides": overrides})
    return make_session(sc)


# -- effects of the preparatory phases ------------------------------------------


def test_support_statements_lower_reluctance():
    s, clf, _ = child(reluctance=0.6)
    before = s.state.reluctance
    ask(s, clf, "Tu m'aides beaucoup.", H("support", phase="rapport"))
    ask(s, clf, "Merci d'être venu.", H("support", phase="rapport"))
    assert s.state.reluctance < before - 0.1


def test_ground_rules_lower_acquiescence_with_a_ceiling():
    s, clf, _ = child(suggestibility=0.8)
    levels = [s.state.acquiescence]
    for i in range(5):
        ask(s, clf, f"Règle {i}", H("ground_rule", phase="ground_rules"))
        levels.append(s.state.acquiescence)
    assert levels[1] < levels[0] and levels[3] < levels[2]
    assert levels[3] == levels[4] == levels[5]  # max_effective_ground_rules = 3


def test_ground_rules_make_false_suggestions_less_successful():
    def acquiescence_rate(rules):
        hits = 0
        base = with_profile(load_scenario(S01), suggestibility=0.8)
        for seed in range(300):
            s, clf, _ = make_session(base, seed=seed)
            for i in range(rules):
                ask(s, clf, f"Règle {i}", H("ground_rule", phase="ground_rules"))
            r = ask(s, clf, "Il avait un couteau, hein ?", H("suggestive", OUT_OF_SCENARIO, suggested_proposition="il avait un couteau"))
            hits += r.decision.speech_act == SpeechAct.ACQUIESCE
        return hits / 300

    assert acquiescence_rate(3) < acquiescence_rate(0) - 0.1


def test_narrative_practice_makes_later_invitations_richer():
    plain, clf, _ = child(verbal_skills=0.45)
    r_plain = ask(plain, clf, "Raconte-moi.", H("invitation", phase="substantive"))

    practiced, clf2, _ = child(verbal_skills=0.45)
    for i in range(3):
        ask(practiced, clf2, f"Raconte ton anniversaire {i}.", H("invitation", phase="narrative_practice"))
    assert practiced.state.verbosity > plain.state.verbosity
    r_practiced = ask(practiced, clf2, "Raconte-moi.", H("invitation", phase="substantive"))
    assert len(r_practiced.decision.allowed_units) > len(r_plain.decision.allowed_units)


# -- disclosure threshold ----------------------------------------------------------


def test_reluctant_child_needs_several_transition_prompts():
    s, clf, _ = child(reluctance=0.6)  # threshold 3.0 with open prompts of pressure 1.0
    acts = [
        ask(s, clf, f"Dis-moi pourquoi tu es venu {i}.", H("invitation", phase="transition")).decision
        for i in range(3)
    ]
    assert [d.speech_act for d in acts] == [SpeechAct.RELUCTANT, SpeechAct.RELUCTANT, SpeechAct.ANSWER]
    assert acts[2].disclosure and not acts[2].forced_disclosure
    assert s.phase == Phase.SUBSTANTIVE
    assert ViolationKind.FORCED_DISCLOSURE not in [v.kind for v in s.phases.violations]


def test_reluctant_answers_reveal_nothing():
    s, clf, _ = child(reluctance=0.6)
    r = ask(s, clf, "Dis-moi pourquoi tu es là.", H("invitation", phase="transition"))
    assert r.decision.allowed_units == [] and s.state.revealed == []
    assert r.phase == Phase.TRANSITION


def test_support_during_transition_lowers_the_threshold():
    without, clf, _ = child(reluctance=0.6)
    with_support, clf2, _ = child(reluctance=0.6)
    for i in range(3):
        ask(with_support, clf2, f"Tu es courageux {i}.", H("support", phase="transition"))
    a = ask(without, clf, "Dis-moi pourquoi tu es là.", H("invitation", phase="transition"))
    b = ask(with_support, clf2, "Dis-moi pourquoi tu es là.", H("invitation", phase="transition"))
    b2 = ask(with_support, clf2, "Raconte-moi.", H("invitation", phase="transition"))
    assert a.decision.speech_act == SpeechAct.RELUCTANT
    assert SpeechAct.ANSWER in (b.decision.speech_act, b2.decision.speech_act)


def test_suggestive_prompt_can_force_disclosure_and_is_flagged():
    s, clf, _ = child(reluctance=0.5, p_acquiesce=1.0, suggestibility_multiplier_range=[1, 1])  # threshold 2.5
    r = ask(s, clf, "Le monsieur a poussé Monsieur Bertin, hein ?", H("suggestive", "d_pousse", phase="transition", suggested_proposition="il a poussé Monsieur Bertin"))
    assert r.decision.disclosure and r.decision.forced_disclosure
    assert [(v.kind, v.phase) for v in r.violations if v.kind == ViolationKind.FORCED_DISCLOSURE] == [
        (ViolationKind.FORCED_DISCLOSURE, Phase.SUBSTANTIVE)
    ]


def test_very_reluctant_child_may_never_disclose():
    s, clf, _ = child(reluctance=0.95)
    for i in range(10):
        r = ask(s, clf, f"Est-ce que quelqu'un t'a fait du mal {i} ?", H("suggestive", "d_pousse", phase="transition", suggested_proposition="quelqu'un lui a fait du mal"))
        assert r.decision.speech_act == SpeechAct.RELUCTANT
    assert s.state.revealed == [] and s.state.contaminated == []
    assert s.phase == Phase.TRANSITION


def test_rapport_and_neutral_prompts_do_not_count_as_pressure():
    s, clf, _ = child(reluctance=0.6)
    ask(s, clf, "Qu'est-ce que tu aimes faire ?", H("invitation", phase="rapport"))
    ask(s, clf, "Raconte ton anniversaire.", H("invitation", phase="narrative_practice"))
    ask(s, clf, "C'était quoi le gâteau ?", H("directive", "n_gateau", phase="narrative_practice"))
    assert s.state.disclosure_pressure == 0


# -- closure ---------------------------------------------------------------------


def test_anything_else_question_may_reveal_a_remaining_central_unit():
    s, clf, _ = child(p_closure_reveal=1.0)
    ask(s, clf, "Raconte.", H("invitation", phase="substantive"))
    r = ask(s, clf, "Y a-t-il autre chose que je devrais savoir ?", H("invitation", phase="closure"))
    assert r.decision.speech_act == SpeechAct.ANSWER and len(r.decision.allowed_units) == 1
    assert r.decision.allowed_units[0].id == "d_messieurs"  # next remaining central unit


def test_anything_else_question_usually_gets_nothing_more():
    s, clf, _ = child(p_closure_reveal=0.0)
    ask(s, clf, "Raconte.", H("invitation", phase="substantive"))
    r = ask(s, clf, "Autre chose ?", H("invitation", phase="closure"))
    assert r.decision.speech_act == SpeechAct.DENY


def test_soft_turn_limit_warns_once_without_interrupting():
    s, clf, _ = make_session()
    notices = []
    for i in range(SOFT_TURN_LIMIT + 3):
        notices.append(ask(s, clf, f"Hmm {i}", C("facilitator")).notices)
    assert [i for i, n in enumerate(notices) if n] == [SOFT_TURN_LIMIT - 1]
    assert len(s.log.turns) == SOFT_TURN_LIMIT + 3
