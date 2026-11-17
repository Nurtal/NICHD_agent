"""Arousal, expressive delivery and demeanor (ADR 0003)."""

import random
from pathlib import Path

import pytest
from doubles import C, ask, make_session, with_profile

from nichd_sim.delivery import ChunkKind, Delivery, HesitationCause, plan_speech, render_plan
from nichd_sim.demeanor import Cue, CueFamily, Intensity, make_demeanor
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import AgeBand, ExpressionStyle, Scenario, load_scenario

ROOT = Path(__file__).resolve().parent.parent
S01 = ROOT / "scenarios" / "s01_bagarre_parc.yaml"
S02 = ROOT / "scenarios" / "s02_violences_maison.yaml"
S08 = ROOT / "scenarios" / "s08_violences_maison_secret.yaml"
R = HesitationCause


def overridden(sc: Scenario, **overrides) -> Scenario:
    return sc.model_copy(update={"parameter_overrides": {**sc.parameter_overrides, **overrides}})


def s08(strength: float, **profile) -> Scenario:
    sc = load_scenario(S08)
    sc = sc.model_copy(update={"deception": sc.deception.model_copy(update={"strength": strength})})
    return with_profile(sc, **profile) if profile else sc


def params(band=AgeBand.B7_9) -> Parameters:
    return Parameters.load(band)


# -- arousal -----------------------------------------------------------------


def test_baseline_comes_from_reluctance_and_age():
    p = params()
    calm, _, _ = make_session(with_profile(load_scenario(S02), reluctance=0.0))
    tense, _, _ = make_session(with_profile(load_scenario(S02), reluctance=1.0))
    assert calm.state.arousal == pytest.approx(p["arousal_base"])
    assert tense.state.arousal == pytest.approx(p["arousal_base"] + p["arousal_reluctance_weight"])
    assert tense.state.arousal == tense.state.arousal_baseline


def test_pressure_on_the_target_event_raises_arousal_and_support_lowers_it():
    s, clf, _ = make_session(with_profile(load_scenario(S02), reluctance=0.0), seed=1)
    start = s.state.arousal
    trace = []
    for i in range(5):
        ask(s, clf, f"q{i}", C("suggestive", "d_bras", suggested_proposition="le cou"))
        trace.append(s.state.arousal)
    assert trace == sorted(trace) and trace[-1] > start + 0.2
    peak = trace[-1]
    for i in range(5):
        ask(s, clf, f"s{i}", C("support"))
    assert s.state.arousal < peak - 0.2


def test_arousal_returns_toward_baseline_on_neutral_turns():
    s, clf, _ = make_session(with_profile(load_scenario(S02), reluctance=0.0), seed=1)
    for i in range(4):
        ask(s, clf, f"q{i}", C("suggestive", "d_bras", suggested_proposition="le cou"))
    high = s.state.arousal
    for i in range(6):
        ask(s, clf, f"n{i}", C("ground_rule"))
    assert s.state.arousal_baseline < s.state.arousal < high


def test_phase_violation_raises_arousal():
    def arousal(violation):
        s, _, _ = make_session(load_scenario(S02), seed=0)
        s.engine.decide(C("ground_rule"), phase_violation=violation)
        return s.engine.state.arousal
    assert arousal(True) > arousal(False)


def test_session_reports_phase_violations_to_the_engine():
    s, clf, _ = make_session(load_scenario(S02), seed=0)
    ask(s, clf, "q", C("directive", "d_bras"))  # focused question during rapport
    assert s.log.phase_violations
    quiet, _, _ = make_session(load_scenario(S02), seed=0)
    quiet.engine.decide(C("directive", "d_bras"))
    assert s.state.arousal > quiet.engine.state.arousal


SCRIPT = [
    C("support"), C("invitation", phase_hints=["rapport"]), C("ground_rule"),
    C("invitation", phase_hints=["narrative_practice"]), C("invitation", phase_hints=["transition"]),
    C("invitation", phase_hints=["transition"]), C("invitation"), C("directive", "d_bras"),
    C("suggestive", "d_tape", suggested_proposition="avec un bâton"), C("option_posing", "d_karim", options=["papa", "Karim"]),
    C("facilitator"), C("support"), C("invitation"), C("cued_invitation", "d_crie"), C("directive", "out_of_scenario"),
]


@pytest.mark.parametrize("path", [S02, S08], ids=["s02", "s08"])
@pytest.mark.parametrize("seed", range(5))
def test_arousal_is_observable_only(path, seed):
    """An extreme arousal changes the body and the voice, never what the child says (ADR 0003, decision 7)."""
    def run(sc):
        s, clf, _ = make_session(sc, seed=seed)
        return [ask(s, clf, f"u{i}", c).decision for i, c in enumerate(SCRIPT)]
    base = load_scenario(path)
    extreme = overridden(base, arousal_base=0.9, arousal_rise={k: 0.9 for k in params()["arousal_rise"]})
    for d0, d1 in zip(run(base), run(extreme)):
        assert d0.model_dump(exclude={"delivery", "demeanor"}) == d1.model_dump(exclude={"delivery", "demeanor"})
    assert run(extreme)[-1].demeanor.arousal > run(base)[-1].demeanor.arousal


# -- no false cue ---------------------------------------------------------------

QUESTIONS = {
    "directive": lambda u: C("directive", u.id),
    "option_posing": lambda u: C("option_posing", u.id, suggested_proposition=u.anchors[0]),
    "suggestive": lambda u: C("suggestive", u.id, suggested_proposition=u.anchors[0]),
}


def lie_truth_pairs(seeds=range(15)):
    """Same session, same question about the same protected fact; only the will to conceal differs."""
    base = load_scenario(S08)
    out = []
    for seed in seeds:
        for uid in base.deception.protected:
            unit = base.unit(uid)
            for make in QUESTIONS.values():
                decisions = []
                for strength in (1.0, 0.0):
                    s, clf, _ = make_session(s08(strength), seed=seed)
                    for i, c in enumerate([C("support"), C("invitation", phase_hints=["transition"]),
                                           C("invitation", phase_hints=["transition"]), C("invitation")]):
                        ask(s, clf, f"w{i}", c)
                    decisions.append(ask(s, clf, "q", make(unit)).decision)
                lie, truth = decisions
                # Same history only: if the truthful child had already told the fact earlier (the
                # lying one omitted it), it is easier to recall — a history difference, not a lie cue.
                if lie.lie is not None and truth.lie is None and all(au.new for au in truth.allowed_units):
                    out.append((lie, truth))
    return out


def test_body_does_not_give_the_lie_away():
    """Controlled pairs: a lie shows exactly the same body as the truth it hides."""
    pairs = lie_truth_pairs()
    assert len(pairs) >= 30
    for lie, truth in pairs:
        assert lie.demeanor == truth.demeanor
        assert lie.delivery.tremor == truth.delivery.tremor


def test_voice_differs_only_through_the_weak_deception_load():
    """False starts may differ (weak deception weight), but rarely: no audible lie detector."""
    pairs = lie_truth_pairs()
    diff = sum(lie.delivery.false_starts - truth.delivery.false_starts for lie, truth in pairs) / len(pairs)
    assert abs(diff) <= 0.2


# -- demeanor -----------------------------------------------------------------


def _draw(arousal, style, n=400, loads=None, band=AgeBand.B7_9):
    p = params(band)
    rng = random.Random(0)
    return [make_demeanor(arousal, loads or {}, style, p, rng) for _ in range(n)]


def _share(demeanors, family):
    return sum(family in d.families() for d in demeanors) / len(demeanors)


def test_frozen_child_shows_little_movement_despite_high_arousal():
    agitated = _draw(0.85, ExpressionStyle.AGITATED)
    frozen = _draw(0.85, ExpressionStyle.FROZEN)
    assert _share(frozen, CueFamily.FIDGET) < _share(agitated, CueFamily.FIDGET) - 0.3
    assert _share(frozen, CueFamily.FREEZE) > 0.5
    assert _share(agitated, CueFamily.FREEZE) == 0
    assert sum(d.has(Cue.GAZE_BLANK) for d in frozen) > sum(d.has(Cue.GAZE_BLANK) for d in agitated)


def test_no_tears_below_the_threshold():
    p = params()
    below = _draw(p["demeanor_tears_arousal"] - 0.01, ExpressionStyle.AGITATED)
    assert _share(below, CueFamily.TEARS) == 0
    assert _share(_draw(0.95, ExpressionStyle.AGITATED), CueFamily.TEARS) > 0.3


def test_calm_child_looks_at_ease_and_upset_child_does_not():
    calm, upset = _draw(0.05, ExpressionStyle.MIXED), _draw(0.8, ExpressionStyle.MIXED)
    assert _share(calm, CueFamily.EASE) > 0.5 and _share(upset, CueFamily.EASE) == 0
    assert sum(d.has(Cue.GAZE_STEADY) for d in calm) > sum(d.has(Cue.GAZE_STEADY) for d in upset)


def test_remembering_turns_the_gaze_away():
    thinking = _draw(0.2, ExpressionStyle.MIXED, loads={R.RETRIEVAL: 0.9})
    plain = _draw(0.2, ExpressionStyle.MIXED)
    assert sum(d.has(Cue.GAZE_AVERTED) for d in thinking) > 2 * sum(d.has(Cue.GAZE_AVERTED) for d in plain)


def test_deception_load_is_ignored_by_the_body():
    a = make_demeanor(0.5, {R.AFFECT: 0.4}, ExpressionStyle.MIXED, params(), random.Random(3))
    b = make_demeanor(0.5, {R.AFFECT: 0.4, R.DECEPTION: 0.8}, ExpressionStyle.MIXED, params(), random.Random(3))
    assert a == b


def test_one_gaze_cue_and_at_most_max_cues_more():
    p = params()
    for d in _draw(0.9, ExpressionStyle.AGITATED, n=200):
        assert d.cues[0].cue.family == CueFamily.GAZE
        assert sum(c.cue.family == CueFamily.GAZE for c in d.cues) == 1
        assert len(d.cues) <= 1 + p["demeanor_max_cues"]
        strengths = [c.intensity for c in d.cues[1:]]
        assert all(i in Intensity for i in strengths)


def test_fixed_number_of_draws_per_turn():
    p = params()
    for arousal, style in [(0.0, ExpressionStyle.MIXED), (1.0, ExpressionStyle.FROZEN), (0.5, ExpressionStyle.AGITATED)]:
        rng = random.Random(7)
        make_demeanor(arousal, {R.RETRIEVAL: 0.5}, style, p, rng)
        ref = random.Random(7)
        for _ in range(2 * 8 + 1):
            ref.random()
        assert rng.random() == ref.random()


def test_style_defaults_by_age_band():
    young = load_scenario(S01)  # 5 years old
    assert young.child_profile.expression_style is None
    s, _, _ = make_session(young)
    assert s.engine.style == ExpressionStyle.AGITATED
    s, _, _ = make_session(with_profile(young, expression_style=ExpressionStyle.FROZEN))
    assert s.engine.style == ExpressionStyle.FROZEN


def test_every_turn_carries_a_demeanor_and_is_deterministic():
    def run(seed):
        s, clf, _ = make_session(load_scenario(S02), seed=seed)
        return [ask(s, clf, f"u{i}", c).decision.demeanor for i, c in enumerate(SCRIPT)]
    assert all(d is not None for d in run(2))
    assert run(2) == run(2)


# -- expressive delivery ------------------------------------------------------------


def test_high_arousal_rushes_an_agitated_child_but_not_a_frozen_one():
    def last_rate(style):
        sc = overridden(with_profile(load_scenario(S02), reluctance=1.0, expression_style=style), arousal_base=0.9)
        s, clf, _ = make_session(sc, seed=0)
        return ask(s, clf, "u", C("ground_rule")).decision.delivery.rate
    assert last_rate(ExpressionStyle.AGITATED) > 1.05
    assert last_rate(ExpressionStyle.FROZEN) < last_rate(ExpressionStyle.AGITATED)


def test_false_start_repeats_the_opening_word():
    d = Delivery(onset_ms=500, false_starts=1)
    plan = plan_speech("il m'a attrapé le bras", d)
    assert [c.text for c in plan if c.kind == ChunkKind.SPEECH] == ["il…", "il m'a attrapé le bras"]
    assert render_plan(plan).startswith("[0,5 s] il…")


def test_false_start_skips_one_word_replies():
    plan = plan_speech("non", Delivery(onset_ms=500, false_starts=2))
    assert [c.text for c in plan if c.kind == ChunkKind.SPEECH] == ["non"]


def test_describe_mentions_the_new_voice_features():
    d = Delivery(onset_ms=500, rate=1.2, false_starts=1, tremor=0.5)
    text = d.describe()
    assert "débit précipité" in text and "faux départ" in text and "voix tremblante" in text


# -- stage direction (PR 3) -------------------------------------------------------

from nichd_sim.demeanor import Demeanor, ShownCue, stage_direction  # noqa: E402
from nichd_sim.delivery import Volume  # noqa: E402
from nichd_sim.feedback import render_text  # noqa: E402


def test_stage_direction_reads_body_then_voice():
    d = Demeanor(cues=[ShownCue(cue=Cue.GAZE_DOWN, intensity=Intensity.CLEAR),
                       ShownCue(cue=Cue.FIDGET_LEGS, intensity=Intensity.CLEAR)])
    voice = Delivery(onset_ms=3000, volume=Volume.LOW, fillers=1)
    assert stage_direction(d, voice) == (
        "Les yeux baissés et les jambes qui s'agitent — après un long silence, à voix basse, en hésitant"
    )


def test_stage_direction_for_a_silence_and_for_old_logs():
    d = Demeanor(cues=[ShownCue(cue=Cue.GAZE_BLANK, intensity=Intensity.STRONG)])
    assert stage_direction(d, Delivery(onset_ms=4000), silent=True) == "Le regard vide, perdu au loin — sans un mot"
    assert stage_direction(None, Delivery(onset_ms=4000)) == ""


def test_stage_direction_never_names_a_cause_or_a_lie():
    """The learner reads the body, not the engine's reasons."""
    for lie, truth in lie_truth_pairs(seeds=range(3)):
        for d in (lie, truth):
            text = stage_direction(d.demeanor, d.delivery).lower()
            assert not any(w in text for w in ("mens", "mémoire", "émotion", "confusion", "activation"))


def test_every_cue_has_three_gender_neutral_phrasings():
    from nichd_sim.demeanor import _PHRASES
    assert set(_PHRASES) == set(Cue)
    for phrases in _PHRASES.values():
        assert len(phrases) == 3 and all(p and p == p.strip() for p in phrases)
        # no masculine-only participles agreeing with the child
        assert not any(w in p.split() for p in phrases for w in ("figé", "absent", "replié", "recroquevillé", "silencieux"))


def test_feedback_transcript_carries_the_stage_direction():
    s, clf, _ = make_session(load_scenario(S02), seed=1)
    for i, c in enumerate(SCRIPT[:6]):
        ask(s, clf, f"u{i}", c)
    fb = s.end().feedback
    assert all(line.stage_direction for line in fb.transcript)
    assert f"({fb.transcript[0].stage_direction})" in render_text(fb)


def test_one_word_reply_is_not_said_stammering():
    d = Demeanor(cues=[ShownCue(cue=Cue.GAZE_DOWN, intensity=Intensity.SLIGHT)])
    voice = Delivery(onset_ms=500, false_starts=1)
    assert "bafouillant" not in stage_direction(d, voice, text="D'accord.")
    assert "bafouillant" in stage_direction(d, voice, text="il m'a attrapé")


def test_low_shaking_voice_is_said_once():
    d = Demeanor(cues=[ShownCue(cue=Cue.GAZE_DOWN, intensity=Intensity.SLIGHT)])
    text = stage_direction(d, Delivery(onset_ms=500, volume=Volume.LOW, tremor=0.6))
    assert "d'une voix basse et tremblante" in text and "à voix basse" not in text
