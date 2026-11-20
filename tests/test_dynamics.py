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
        for name in ("last_act", "last_target", "closed_asked", "last_key", "supports_given"):
            t["state_after"].pop(name, None)
    log = SessionLog.model_validate(data)
    assert replay(log, find_scenario(log)).identical


# -- lot 1: reluctance dynamics ----------------------------------------------------------

from doubles import with_profile  # noqa: E402

from nichd_sim.coaching import build_coaching  # noqa: E402
from nichd_sim.scenario import load_scenario  # noqa: E402

S01 = ROOT / "scenarios" / "s01_bagarre_parc.yaml"


def dyn(seed=0, **profile):
    sc = load_scenario(S01)
    if profile:
        sc = with_profile(sc, **profile)
    return make_session(sc, seed=seed, dynamics=True)


def disclosed(s, clf):
    ask(s, clf, "Raconte-moi tout.", C("invitation"))
    assert s.state.disclosed


def test_pressure_before_disclosure_makes_a_reluctant_child_more_reluctant():
    s, clf, _ = dyn(reluctance=0.6)
    before = s.state.reluctance
    ask(s, clf, "Il t'a poussé, hein ?", C("suggestive", "d_pousse", suggested_proposition="il a poussé"))
    assert s.state.reluctance > before


def test_pressure_is_free_once_the_child_has_disclosed():
    s, clf, _ = dyn(reluctance=0.2)
    disclosed(s, clf)
    before = s.state.reluctance
    ask(s, clf, "Il avait un couteau, hein ?", C("suggestive", OUT_OF_SCENARIO, suggested_proposition="un couteau"))
    assert s.state.reluctance == before


def _dont_know(s, clf, q="Comment il s'appelait ?"):
    """Ask an out-of-scenario question until the child says « je sais pas » (seeded)."""
    r = ask(s, clf, q, C("directive", OUT_OF_SCENARIO))
    return r.decision.speech_act == SpeechAct.DONT_KNOW


def _first_seed_with_dont_know():
    for seed in range(50):
        s, clf, _ = dyn(seed=seed)
        disclosed(s, clf)
        if _dont_know(s, clf):
            return seed
    raise AssertionError("aucun « je sais pas » sur 50 seeds")


def test_rejecting_a_dont_know_raises_reluctance_accepting_it_lowers_it():
    seed = _first_seed_with_dont_know()
    s, clf, _ = dyn(seed=seed)
    disclosed(s, clf)
    _dont_know(s, clf)
    base = s.state.reluctance
    ask(s, clf, "Comment il s'appelait ?", C("directive", OUT_OF_SCENARIO))  # the same question again
    assert s.engine.rejection and s.state.reluctance > base

    s, clf, _ = dyn(seed=seed)
    disclosed(s, clf)
    _dont_know(s, clf)
    ask(s, clf, "D'accord, merci.", C("support"))
    assert not s.engine.rejection and s.state.reluctance < base


def test_a_rejection_makes_the_child_more_compliant_for_that_turn_only():
    seed = _first_seed_with_dont_know()
    s, clf, _ = dyn(seed=seed)
    disclosed(s, clf)
    _dont_know(s, clf)
    plain = s.engine._suggestibility_factor()
    ask(s, clf, "Comment il s'appelait ?", C("directive", OUT_OF_SCENARIO))
    assert s.engine._acq_boost > 0
    ask(s, clf, "D'accord.", C("support"))
    assert s.engine._acq_boost == 0 and s.engine._suggestibility_factor() <= plain


def test_support_lowers_acquiescence_up_to_a_cap():
    s, clf, _ = dyn()
    start = s.state.acquiescence
    for i in range(5):
        ask(s, clf, f"Tu fais de ton mieux {i}.", C("support"))
    cap = s.params["max_effective_supports"]
    assert s.state.supports_given == cap
    assert abs(s.state.acquiescence - max(0.0, start - cap * s.params["support_acquiescence_drop"])) < 1e-6


def test_repeating_an_unanswerable_question_makes_invention_more_likely():
    """Over many seeds, the 3rd identical out-of-scenario question is answered by invention more often
    than the 1st (Krähenbühl et al., 2009)."""
    first = third = 0
    for seed in range(60):
        s, clf, _ = dyn(seed=seed)
        disclosed(s, clf)
        acts = [ask(s, clf, "De quelle couleur était la voiture ?", C("directive", OUT_OF_SCENARIO)).decision.speech_act
                for _ in range(3)]
        first += acts[0] == SpeechAct.CONFABULATE
        third += acts[2] == SpeechAct.CONFABULATE
    assert third > first


def test_a_repeated_true_yes_no_question_can_flip_the_answer():
    flips = 0
    for seed in range(60):
        s, clf, _ = dyn(seed=seed)
        disclosed(s, clf)
        q = C("option_posing", "d_pousse", suggested_proposition="il a poussé")
        ask(s, clf, "Il a poussé ?", q)
        flips += ask(s, clf, "Il a poussé, tu es sûr ?", q).decision.speech_act == SpeechAct.DENY
    assert 0 < flips < 60


def test_reluctance_lowers_how_much_an_invitation_tells():
    calm = sum(len(ask(*dyn(seed=k, reluctance=0.0)[:2], "Raconte.", C("invitation")).decision.allowed_units)
               for k in range(40))
    tense = 0
    for k in range(40):
        s, clf, _ = dyn(seed=k, reluctance=0.3)
        ask(s, clf, "Je suis là pour t'écouter.", C("support"))  # below the disclosure threshold either way
        tense += len(ask(s, clf, "Raconte.", C("invitation")).decision.allowed_units)
    assert tense < calm


def test_new_rules_are_off_on_replay_of_a_log_without_them(monkeypatch):
    """A log written before lot 1 does not list its parameters: they replay neutral."""
    monkeypatch.chdir(ROOT)
    s, clf, _ = dyn(seed=3)
    disclosed(s, clf)
    for _ in range(3):
        ask(s, clf, "Comment il s'appelait ?", C("directive", OUT_OF_SCENARIO))
    data = s.end().model_dump(mode="json")
    neutral = Parameters.neutral_overrides()
    assert replay(SessionLog.model_validate(data), find_scenario(SessionLog.model_validate(data))).identical
    for name in neutral:
        data["parameters"].pop(name)
    params = Parameters.for_log(AgeBand.B4_6, data["parameters"])
    assert all(params[name] == value for name, value in neutral.items())


# -- coaching alerts --------------------------------------------------------------------------


def test_coaching_flags_a_rejected_dont_know_and_a_repeated_question():
    seed = _first_seed_with_dont_know()
    s, clf, _ = dyn(seed=seed)
    disclosed(s, clf)
    _dont_know(s, clf)
    ask(s, clf, "Comment il s'appelait ?", C("directive", OUT_OF_SCENARIO))  # rejection
    ask(s, clf, "Qui a poussé ?", C("directive", "d_pousse"))
    ask(s, clf, "Tu es sûr que c'est lui qui a poussé ?", C("directive", "d_pousse"))  # repetition
    coaching = build_coaching(s.end(), load_scenario(S01))
    kinds = [[a.kind for a in t.alerts] for t in coaching.turns]
    assert "rejected_refusal" in kinds[2]
    assert "repeated_question" in kinds[4]
    assert not any(k in ("rejected_refusal", "repeated_question") for k in kinds[0] + kinds[1] + kinds[3])


# -- lot 2: question forms told apart by skill 0.3.0 -------------------------------------------

from nichd_sim.classification import GroundRuleKind, PracticeKind, QuestionType, SegmentHint  # noqa: E402


def test_asking_for_the_end_tells_the_end_only():
    """« Raconte-moi la fin » used to tell the beginning (avatar demo, Léo)."""
    s, clf, _ = dyn(seed=0)
    disclosed(s, clf)
    r = ask(s, clf, "Raconte-moi la fin.", C("invitation", segment=SegmentHint.AFTER))
    sc = load_scenario(S01)
    after = {u.id for seg, u in sc.target_units() if str(seg) == "after"}
    assert r.decision.allowed_units and {u.id for u in r.decision.allowed_units if not u.contaminated} <= after


def test_a_cued_invitation_with_a_segment_follows_the_segment():
    s, clf, _ = dyn(seed=0)
    disclosed(s, clf)
    r = ask(s, clf, "Tu as parlé du monsieur. Raconte-moi ce qui s'est passé avant.",
            C("cued_invitation", "d_messieurs", segment=SegmentHint.BEFORE))
    sc = load_scenario(S01)
    before = {u.id for seg, u in sc.target_units() if str(seg) == "before"}
    assert {u.id for u in r.decision.allowed_units if not u.contaminated} <= before


def test_knowledge_questions_often_get_a_bare_yes_more_so_for_the_youngest():
    def bare_yes(age):
        n = 0
        for seed in range(80):
            s, clf, _ = dyn(seed=seed, age=age)
            disclosed(s, clf)
            r = ask(s, clf, "Tu te souviens qui a poussé ?", C("option_posing", "d_pousse", knowledge_question=True))
            n += r.decision.speech_act == SpeechAct.AFFIRM
        return n
    young, old = bare_yes(5), bare_yes(11)
    assert young > old > 0


def test_a_knowledge_question_not_answered_by_yes_is_answered_like_a_directive():
    for seed in range(40):
        s, clf, _ = dyn(seed=seed)
        disclosed(s, clf)
        r = ask(s, clf, "Tu sais qui a poussé ?", C("option_posing", "d_pousse", knowledge_question=True))
        if r.decision.speech_act != SpeechAct.AFFIRM:
            assert r.decision.speech_act == SpeechAct.ANSWER
            assert [u.id for u in r.decision.allowed_units] == ["d_pousse"]
            assert not r.decision.lucky_suggestion  # nothing was suggested
            return
    raise AssertionError("toujours « oui » sur 40 seeds")


def test_a_why_question_is_never_answered_by_yes_or_no():
    """« Ben non » answered a « pourquoi » in a demo: a causal closed question is treated as open."""
    for seed in range(30):
        s, clf, _ = dyn(seed=seed)
        disclosed(s, clf)
        r = ask(s, clf, "Pourquoi il l'a poussé ?", C("option_posing", OUT_OF_SCENARIO, causal=True,
                                                   suggested_proposition="il l'a poussé"))
        assert r.decision.speech_act not in (SpeechAct.DENY, SpeechAct.ACQUIESCE, SpeechAct.AFFIRM)
        assert r.decision.effective_type == QuestionType.DIRECTIVE


def test_a_stated_ground_rule_counts_less_than_a_practised_one():
    def acquiescence(kind):
        s, clf, _ = dyn(age=11)
        ask(s, clf, "Règle.", C("ground_rule", ground_rule_kind=kind, phase_hints=["ground_rules"]))
        return s.state.acquiescence
    start = dyn(age=11)[0].state.acquiescence
    stated, practised = acquiescence(GroundRuleKind.DONT_KNOW), acquiescence(GroundRuleKind.PRACTICE)
    assert practised < stated < start


def test_truth_and_promise_do_not_lower_acquiescence():
    for kind in (GroundRuleKind.TRUTH, GroundRuleKind.PROMISE):
        s, clf, _ = dyn()
        start = s.state.acquiescence
        ask(s, clf, f"Règle {kind}.", C("ground_rule", ground_rule_kind=kind, phase_hints=["ground_rules"]))
        assert s.state.acquiescence == start and s.state.ground_rules_given == 0


def test_an_unknown_ground_rule_kind_keeps_the_full_effect():
    """Older classifiers do not give the kind: same effect as before skill 0.3.0."""
    s, clf, _ = dyn()
    start = s.state.acquiescence
    ask(s, clf, "Règle.", C("ground_rule", phase_hints=["ground_rules"]))
    assert abs(start - s.state.acquiescence - s.params["ground_rule_acquiescence_drop"]) < 1e-9


def test_only_episodic_narrative_practice_raises_verbosity():
    for kind, rises in ((PracticeKind.EPISODIC, True), (PracticeKind.GENERIC, False)):
        s, clf, _ = dyn()
        start = s.state.verbosity
        ask(s, clf, "Raconte-moi.", C("invitation", practice_kind=kind, phase_hints=["narrative_practice"]))
        assert (s.state.verbosity > start) is rises
