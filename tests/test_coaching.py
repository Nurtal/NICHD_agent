"""Protocol coaching for the learner's screen (ADR 0004, addendum)."""

import json
from pathlib import Path

from doubles import C, ask, make_session
from test_demeanor import S02, s08

from nichd_sim.cli import main
from nichd_sim.coaching import Level, build_coaching
from nichd_sim.phases import Phase, PhaseViolation, ViolationKind
from nichd_sim.scenario import load_scenario

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = [
    C("support"), C("ground_rule"), C("invitation", phase_hints=["transition"]), C("invitation"),
    C("suggestive", "d_tape", suggested_proposition="avec un bâton"), C("option_posing", "d_karim", options=["papa", "Karim"]),
    C("compound", inner_type="suggestive"), C("facilitator"),
]


def run(scenario, script=SCRIPT, seed=1, **kw):
    s, clf, _ = make_session(scenario, seed=seed, **kw)
    for i, c in enumerate(script):
        ask(s, clf, f"u{i}", c)
    return s.end()


def s02():
    return load_scenario(S02)


def with_decision(log, index, **update):
    turns = [
        t.model_copy(update={"decision": t.decision.model_copy(update=update)}) if t.index == index else t
        for t in log.turns
    ]
    return log.model_copy(update={"turns": turns})


def test_each_sentence_gets_a_tag_and_a_level():
    c = build_coaching(run(s02()), s02())
    assert [t.tag.level for t in c.turns] == [
        Level.OK, Level.OK, Level.OK, Level.OK, Level.ALERT, Level.WATCH, Level.ALERT, Level.OK,
    ]
    assert c.turns[4].tag.label == "question suggestive"
    assert c.turns[4].alerts[0].message == "Question suggestive" and c.turns[4].alerts[0].hint
    assert c.turns[0].alerts == []
    assert [p.id for p in c.phases] == list(Phase)


def test_phase_shortcuts_raise_alerts_on_the_turn_they_happen():
    log = run(s02())
    c = build_coaching(log, s02())
    kinds = {t.turn: {a.kind for a in t.alerts} for t in c.turns}
    assert ViolationKind.SKIPPED_PHASE.value in kinds[3]
    assert any("clôture" in issue.lower() for issue in c.debrief.issues)


def test_premature_focused_question_is_an_alert():
    script = [C("support"), C("directive", "d_bras")]
    c = build_coaching(run(s02(), script), s02())
    assert c.turns[1].tag.level == Level.ALERT
    assert ViolationKind.PREMATURE_FOCUSED_QUESTION.value in {a.kind for a in c.turns[1].alerts}


def test_counter_is_cumulative_and_ends_on_the_real_total():
    log = run(s02())
    c = build_coaching(log, s02())
    counts = [t.facts_found for t in c.turns]
    assert counts == sorted(counts) and counts[0] == 0
    assert c.facts_total == len(list(s02().target_units())) and not c.facts_hidden
    assert counts[-1] == c.debrief.facts_found > 0


def test_a_lucky_suggestion_counts_only_in_the_debrief():
    log = run(s02())
    plain = build_coaching(log, s02())
    turn = next(t.turn for t, prev in zip(plain.turns[1:], plain.turns) if t.facts_found > prev.facts_found)
    c = build_coaching(with_decision(log, turn, lucky_suggestion=True), s02())
    assert c.turns[turn - 1].facts_found == c.turns[turn - 2].facts_found
    assert c.debrief.facts_found == plain.debrief.facts_found
    assert c.turns[-1].facts_found < c.debrief.facts_found


def test_forced_disclosure_waits_for_the_debrief():
    log = run(s02())
    v = PhaseViolation(kind=ViolationKind.FORCED_DISCLOSURE, phase=Phase.SUBSTANTIVE, turn=5, detail="suggestive")
    c = build_coaching(log.model_copy(update={"phase_violations": [*log.phase_violations, v]}), s02())
    assert all(a.kind != ViolationKind.FORCED_DISCLOSURE.value for t in c.turns for a in t.alerts)
    assert any("dévoilement" in issue.lower() for issue in c.debrief.issues)


def test_violations_caused_by_a_disclosure_are_not_live():
    """The phase jump follows the child's true disclosure: alerting would vouch for what the child said."""
    log = run(s02())
    v = PhaseViolation(kind=ViolationKind.SKIPPED_PHASE, phase=log.turns[0].asked_in, turn=1)
    c = build_coaching(log.model_copy(update={"phase_violations": [v]}), s02())
    assert c.turns[0].alerts == [] and len(c.debrief.issues) == 1


def test_hidden_facts_keep_the_counter_masked_and_the_turns_free_of_causes():
    sc = s08(1.0, reluctance=0.0)
    script = [C("support"), C("invitation", phase_hints=["transition"]),
              C("option_posing", "d_bras", suggested_proposition="bras"),
              C("suggestive", "d_tape", suggested_proposition="avec un bâton")]
    log = run(sc, script, seed=4)
    assert any(t.decision.lie is not None for t in log.turns)
    c = build_coaching(log, sc)
    assert c.facts_hidden and all(t.facts_found is None for t in c.turns) and c.facts_total > 0
    text = json.dumps([t.model_dump(mode="json") for t in c.turns], ensure_ascii=False).lower()
    for word in ("mensonge", "lucky", "contamin", "d_bras", "d_tape", "bâton", "concealment", "deception"):
        assert word not in text, word


def test_turn_coaching_does_not_depend_on_the_child():
    """Same learner sentences, a child who lies or not: the same tags and alerts during the interview."""
    script = [C("support"), C("invitation", phase_hints=["transition"]), C("option_posing", "d_bras"), C("directive", "d_tape")]
    lying, honest = s08(1.0, reluctance=0.0), s08(0.0, reluctance=0.0)
    a, b = build_coaching(run(lying, script, seed=4), lying), build_coaching(run(honest, script, seed=4), honest)
    assert [t.model_dump() for t in a.turns] == [t.model_dump() for t in b.turns]


def test_export_writes_coaching_beside_an_unchanged_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    log_dir = tmp_path / "logs"
    run(s02(), log_dir=log_dir)
    log_path = next(log_dir.glob("*.json"))
    out = tmp_path / "out"
    assert main(["export-avatar", str(log_path), "-o", str(out)]) == 0
    coaching = json.loads((out / "coaching.json").read_text(encoding="utf-8"))
    assert coaching["format"] == 1 and len(coaching["turns"]) == len(SCRIPT)
    perf = (out / "performance.json").read_text(encoding="utf-8")
    assert "facts_found" not in perf and '"tag"' not in perf


def test_export_without_the_scenario_writes_no_coaching(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    log_dir = tmp_path / "logs"
    run(s02(), log_dir=log_dir)
    log_path = next(log_dir.glob("*.json"))
    out = tmp_path / "out"
    empty = tmp_path / "none"
    empty.mkdir()
    assert main(["export-avatar", str(log_path), "-o", str(out), "--scenarios-dir", str(empty)]) == 0
    assert (out / "performance.json").exists() and not (out / "coaching.json").exists()
