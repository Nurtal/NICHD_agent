"""The rule catalogue and its per-session configuration (model control panel, lot R1)."""

from __future__ import annotations

import random

import pytest
from doubles import ROOT, S01, C, ask, make_session

from nichd_sim.delivery import HesitationCause
from nichd_sim.demeanor import Cue, make_demeanor
from nichd_sim.parameters import Parameters, _default_table
from nichd_sim.replay import find_scenario, replay
from nichd_sim.rules import Catalogue, RuleConfig, RuleError, list_presets, load_catalogue
from nichd_sim.scenario import AgeBand, ExpressionStyle, load_scenario
from nichd_sim.session import SessionLog

S08 = ROOT / "scenarios" / "s08_violences_maison_secret.yaml"
PROMOTED = {"gaze_recall_weight", "gaze_averted_weights", "gaze_down_weights", "gaze_steady_floor",
            "cue_arousal_thresholds", "withdrawal_arousal_weight", "fidget_weights"}


# -- catalogue ------------------------------------------------------------------


def test_every_registry_parameter_belongs_to_exactly_one_rule():
    catalogue = load_catalogue()  # validate_against raises otherwise
    owned = [name for rule in catalogue.rules.values() for name in rule.params]
    assert sorted(owned) == sorted(_default_table())


def test_every_switchable_rule_has_something_to_switch_off():
    catalogue, table = load_catalogue(), _default_table()
    for rid, rule in catalogue.rules.items():
        if rule.toggle:
            assert catalogue.off_values(rid, table), rid


def test_slider_ranges_hold_the_default_of_every_age_band():
    table = _default_table()
    for rule in load_catalogue().rules.values():
        for name, spec in rule.params.items():
            if spec.range is None:
                continue
            lo, hi, step = spec.range
            assert lo < hi and step > 0, name
            for band in AgeBand:
                value = table[name].for_band(band)
                values = value.values() if isinstance(value, dict) else value if isinstance(value, list) else [value]
                for v in values:
                    assert lo <= v <= hi, f"{name} ({band}) : {v} hors de [{lo}, {hi}]"


def test_every_reference_is_known_and_links_only_through_a_doi():
    catalogue = load_catalogue()
    for rule in catalogue.rules.values():
        assert rule.family in catalogue.families
        for ref in rule.refs:
            r = catalogue.references[ref]
            assert r.url is None or r.url == f"https://doi.org/{r.doi}"
    assert catalogue.references["doherty_sneddon2005"].url == "https://doi.org/10.3758/BF03195338"


def test_catalogue_rejects_an_orphan_parameter_and_an_unknown_reference():
    raw = load_catalogue().model_dump()
    raw["rules"]["gaze_recall"]["refs"] = ["inconnu"]
    del raw["rules"]["ease"]
    with pytest.raises(RuleError) as e:
        Catalogue.model_validate(raw).validate_against(_default_table())
    assert "référence inconnue" in str(e.value) and "demeanor_ease_arousal" in str(e.value)


# -- promoted constants -----------------------------------------------------------


def test_promoted_constants_replay_older_logs_with_their_former_value():
    table = _default_table()
    for name in PROMOTED:
        assert table[name].has_legacy and not table[name].has_neutral, name
        assert table[name].legacy == table[name].value, name
    old = Parameters.for_log(AgeBand.B7_9, {})
    assert old["gaze_recall_weight"] == 0.6


def test_switching_off_gaze_recall_removes_the_averted_gaze_of_remembering():
    band = AgeBand.B7_9
    on = Parameters.load(band)
    off = RuleConfig(disabled=["gaze_recall", "gaze_emotion"]).parameters(band)
    loads = {HesitationCause.RETRIEVAL: 1.0}

    def averted(p):
        return sum(make_demeanor(0.0, loads, ExpressionStyle.MIXED, p, random.Random(i)).has(Cue.GAZE_AVERTED)
                   for i in range(300))

    assert averted(on) > 100
    assert averted(off) == 0


def test_switching_off_body_cues_leaves_only_the_gaze():
    p = RuleConfig(disabled=["body_cues"]).parameters(AgeBand.B4_6)
    for i in range(100):
        d = make_demeanor(0.95, {}, ExpressionStyle.AGITATED, p, random.Random(i), expressivity=1.0)
        assert len(d.cues) == 1 and d.cues[0].cue.family == "gaze"


# -- configuration and presets ---------------------------------------------------


def test_a_disabled_rule_takes_its_neutral_or_switch_off_values_and_keeps_the_others():
    cfg = RuleConfig(disabled=["refusal_reaction", "memory_effort"], overrides={"p_leak": 0.5})
    p = cfg.parameters(AgeBand.B7_9)
    assert p["rejection_reluctance_rise"] == 0 and p["acceptance_reluctance_drop"] == 0
    assert set(p["retrieval_difficulty"].values()) == {0}
    assert p["retrieval_age_factor"] == 0.8  # not switched off: unchanged
    assert p["p_leak"] == 0.5


def test_a_partial_dict_switch_off_keeps_the_other_keys():
    p = RuleConfig(disabled=["gaze_emotion"]).parameters(AgeBand.B7_9)
    assert p["gaze_down_weights"] == {"arousal": 0, "base": 0.1}


def test_overrides_can_target_one_age_band_and_come_after_the_scenario():
    cfg = RuleConfig(overrides={"p_yes_bias": {"4_6": 0.9}, "p_acquiesce": 0.4})
    assert cfg.parameters(AgeBand.B4_6)["p_yes_bias"] == 0.9
    assert cfg.parameters(AgeBand.B7_9)["p_yes_bias"] == 0.1
    assert cfg.parameters(AgeBand.B7_9, base={"p_acquiesce": 0.05, "p_leak": 0.3})["p_acquiesce"] == 0.4
    assert cfg.parameters(AgeBand.B7_9, base={"p_leak": 0.3})["p_leak"] == 0.3


def test_config_rejects_unknown_rules_parameters_and_base_mechanics():
    with pytest.raises(RuleError, match="règle inconnue"):
        RuleConfig(disabled=["nope"]).check()
    with pytest.raises(RuleError, match="paramètre inconnu"):
        RuleConfig(overrides={"nope": 1}).check()
    with pytest.raises(RuleError, match="ne se désactive pas"):
        RuleConfig(disabled=["disclosure_gate"]).check()


def test_preset_round_trip(tmp_path):
    cfg = RuleConfig(name="très suggestible", description="d", disabled=["leak"],
                     overrides={"p_acquiesce": {"7_9": 0.5}})
    path = cfg.save(tmp_path / "tres-suggestible.yaml")
    assert RuleConfig.load(path) == cfg
    assert list(list_presets(tmp_path)) == ["tres-suggestible"]
    (tmp_path / "bad.yaml").write_text("disabled: [nope]\n", encoding="utf-8")
    with pytest.raises(RuleError):
        RuleConfig.load(tmp_path / "bad.yaml")


def test_shipped_presets_load():
    presets = list_presets(ROOT / "presets")
    assert {"moteur-de-base", "sans-signaux-non-verbaux"} <= set(presets)
    for path in presets.values():
        RuleConfig.load(path)


def test_base_engine_preset_matches_the_neutral_overrides():
    cfg = RuleConfig.load(ROOT / "presets" / "moteur-de-base.yaml")
    p = cfg.parameters(AgeBand.B7_9)
    for name, value in Parameters.neutral_overrides().items():
        assert p[name] == value, name


# -- session log -------------------------------------------------------------------


def test_a_session_with_its_own_profile_and_rules_replays_identically(monkeypatch):
    monkeypatch.chdir(ROOT)
    sc = load_scenario(S08)
    profile = sc.child_profile.model_copy(update={"reluctance": 0.2, "suggestibility": 0.95})
    sc = sc.model_copy(update={"child_profile": profile,
                               "deception": sc.deception.model_copy(update={"strength": 0.3})})
    cfg = RuleConfig(name="essai", disabled=["promise", "gaze_recall"], overrides={"p_acquiesce": 0.6})
    s, clf, _ = make_session(sc, seed=4, params=cfg.parameters(profile.age_band), rules=cfg.summary())
    for i, c in enumerate([C("support"), C("invitation"), C("suggestive", "d_tape"), C("invitation"),
                           C("option_posing", "d_tape"), C("directive", "d_bras")]):
        ask(s, clf, f"u{i}", c)
    log = SessionLog.model_validate_json(s.end().model_dump_json())
    assert log.profile["child_profile"]["reluctance"] == 0.2
    assert log.profile["deception_strength"] == 0.3
    assert log.rules == {"preset": "essai", "disabled": ["gaze_recall", "promise"], "adjusted": ["p_acquiesce"]}
    assert log.parameters["promise_concealment_drop"] == 0
    report = replay(log, find_scenario(log))  # the sheet's profile differs: the log's is applied
    assert report.identical, report.mismatches


def test_a_format_7_log_without_profile_or_promoted_parameters_still_replays(monkeypatch):
    monkeypatch.chdir(ROOT)
    s, clf, _ = make_session(load_scenario(S01), seed=2, dynamics=True)
    for i, c in enumerate([C("support"), C("invitation"), C("directive", "d_pousse"), C("invitation")]):
        ask(s, clf, f"u{i}", c)
    data = s.end().model_dump(mode="json")
    data.update(log_format=7, profile=None, rules=None)
    data["parameters"] = {k: v for k, v in data["parameters"].items() if k not in PROMOTED}
    log = SessionLog.model_validate(data)
    assert replay(log, find_scenario(log)).identical


# -- command line ------------------------------------------------------------------------


def test_play_with_a_preset_logs_its_rules(tmp_path, monkeypatch):
    import io

    from nichd_sim.cli import main
    from nichd_sim.replay import load_log

    monkeypatch.setattr("sys.stdin", io.StringIO("/fin\n"))
    preset = ROOT / "presets" / "moteur-de-base.yaml"
    assert main(["play", str(S01), "--preset", str(preset), "--no-rephrase", "--log-dir", str(tmp_path)]) == 0
    log = load_log(next(tmp_path.glob("*.json")))
    assert log.rules["preset"] == "Moteur de base" and "leak" in log.rules["disabled"]
    assert log.parameters["p_leak"] == 0
    assert main(["play", str(S01), "--preset", str(tmp_path / "absent.yaml")]) == 2
