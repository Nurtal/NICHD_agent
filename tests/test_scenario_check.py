"""Scenario authoring checks (#29)."""


from doubles import S01
from nichd_sim.cli import main
from nichd_sim.scenario import load_scenario
from nichd_sim.scenario_check import Level, check_scenario


def mutate_unit(sc, unit_id, **changes):
    events = {}
    for name in ("target_event", "neutral_event"):
        ev = getattr(sc, name)
        segs = [
            seg.model_copy(update={"units": [u.model_copy(update=changes) if u.id == unit_id else u for u in seg.units]})
            for seg in ev.segments
        ]
        events[name] = ev.model_copy(update={"segments": segs})
    return sc.model_copy(update=events)


def messages(findings, level):
    return [(f.unit, f.message) for f in findings if f.level == level]


def test_clean_scenario_has_only_the_draft_notice():
    findings = check_scenario(load_scenario(S01))
    assert [f.level for f in findings] == [Level.INFO]


def test_anchor_absent_from_value_is_an_error():
    sc = mutate_unit(load_scenario(S01), "d_chien", anchors=["chat"])
    errors = messages(check_scenario(sc), Level.ERROR)
    assert errors and errors[0][0] == "d_chien" and "omission" in errors[0][1]


def test_forbidden_term_in_a_value_is_an_error():
    sc = mutate_unit(load_scenario(S01), "d_chien", value="le chien était tout nu", anchors=["chien"])
    assert any("lexique interdit" in m for _, m in messages(check_scenario(sc), Level.ERROR))


def test_common_and_shared_anchors_are_warnings():
    sc = mutate_unit(load_scenario(S01), "d_chien", value="le chien aboyait à la maison", anchors=["chien", "maison"])
    sc = mutate_unit(sc, "d_banc", value="c'était à côté du banc, il y avait le chien", anchors=["banc", "chien"])
    warnings = messages(check_scenario(sc), Level.WARNING)
    assert ("d_chien", "ancre trop courante 'maison' : fausses fuites probables") in warnings
    assert any(u in ("d_banc", "d_chien") and "partagée" in m for u, m in warnings)


def test_thin_target_event_and_missing_neutral_event_are_warnings():
    sc = load_scenario(S01)
    first = sc.target_event.segments[0]
    thin = sc.model_copy(update={"target_event": sc.target_event.model_copy(update={"segments": [first]}),
                                 "neutral_event": None})
    warnings = " ".join(m for _, m in messages(check_scenario(thin), Level.WARNING))
    assert "unité(s) centrale(s)" in warnings and "événement neutre" in warnings


def test_never_disclosing_profile_is_a_warning():
    sc = load_scenario(S01)
    sc = sc.model_copy(update={"child_profile": sc.child_profile.model_copy(update={"reluctance": 0.95})})
    assert any("ne dévoilera jamais" in m for _, m in messages(check_scenario(sc), Level.WARNING))


def test_cli_exit_code(tmp_path, capsys):
    assert main(["check-scenario", str(S01)]) == 0
    bad = tmp_path / "bad.yaml"
    bad.write_text(S01.read_text().replace("anchors: [chien, aboyait]", "anchors: [chat]"))
    assert main(["check-scenario", str(bad)]) == 1
    assert "erreur [d_chien]" in capsys.readouterr().out
