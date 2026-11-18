"""Performance contract for the avatar (ADR 0004)."""

import json
from pathlib import Path

import pytest
from doubles import C, ask, make_session
from test_demeanor import SCRIPT, S02, s08

from nichd_sim.cli import main
from nichd_sim.delivery import ChunkKind
from nichd_sim.performance import (
    PERFORMANCE_FORMAT, SessionPerformance, build_session, build_turn, estimate_timeline, json_schema, write_session,
)
from nichd_sim.replay import load_log
from nichd_sim.scenario import load_scenario
from nichd_sim.voice import ToneSpeaker, render_speech
from nichd_sim.delivery import plan_speech

ROOT = Path(__file__).resolve().parent.parent
MVP_LOGS = sorted((ROOT / "tests" / "fixtures" / "mvp_logs").glob("*.json"))


def session_log(sc=None, seed=1, script=SCRIPT):
    s, clf, _ = make_session(sc or load_scenario(S02), seed=seed)
    for i, c in enumerate(script):
        ask(s, clf, f"u{i}", c)
    return s.end()


def _check_timeline(spans):
    assert spans and spans[0].start_ms == 0
    for a, b in zip(spans, spans[1:]):
        assert a.end_ms == b.start_ms
    assert all(s.end_ms >= s.start_ms for s in spans)


def test_estimated_timeline_keeps_exact_silences():
    log = session_log()
    for t in log.turns:
        p = build_turn(t)
        _check_timeline(p.timeline)
        assert p.timing == "estimated" and p.duration_ms == p.timeline[-1].end_ms
        plan = plan_speech(t.response, t.decision.delivery)
        assert [s.end_ms - s.start_ms for s in p.timeline if s.kind == ChunkKind.SILENCE] == [
            c.ms for c in plan if c.kind == ChunkKind.SILENCE
        ]


def test_audio_timeline_is_taken_from_the_rendered_audio():
    t = session_log().turns[6]
    rendered = render_speech(plan_speech(t.response, t.decision.delivery), ToneSpeaker(), t.decision.delivery)
    p = build_turn(t, rendered, audio="turn_007.wav")
    assert p.timing == "audio" and p.audio == "turn_007.wav"
    assert [(s.start_ms, s.end_ms) for s in p.timeline] == [(s.start_ms, s.end_ms) for s in rendered.timeline]


def test_body_and_voice_come_from_the_decision():
    t = session_log().turns[8]
    p = build_turn(t)
    d = t.decision
    assert p.body.arousal == d.demeanor.arousal and len(p.body.cues) == len(d.demeanor.cues)
    assert p.body.cues[0].family == "gaze"
    assert p.voice.rate == d.delivery.rate and p.voice.volume == str(d.delivery.volume)
    assert p.stage_direction


def test_contract_carries_no_cause_and_no_lie():
    """A body shows the child; it never gets the engine's reasons (no lie detector downstream)."""
    log = session_log(s08(1.0, reluctance=0.0), seed=4, script=[
        C("support"), C("invitation", phase_hints=["transition"]),
        C("option_posing", "d_bras", suggested_proposition="bras"), C("suggestive", "d_tape", suggested_proposition="avec un bâton"),
    ])
    assert any(t.decision.lie is not None for t in log.turns)
    text = json.dumps(build_session(log, "Emma", 8).model_dump(mode="json")).lower()
    for word in ("lie", "mensonge", "deception", "concealment", "loads", "reason", "retrieval", "affect"):
        assert f'"{word}' not in text, word


@pytest.mark.parametrize("path", MVP_LOGS[:3], ids=lambda p: p.stem)
def test_old_logs_export_with_an_empty_body(path):
    perf = build_session(load_log(path), "Léo", 5)
    assert perf.turns and all(t.body.arousal is None and t.body.cues == [] for t in perf.turns)
    for t in perf.turns:
        _check_timeline(t.timeline) if t.timeline else None


def test_session_round_trips_and_matches_its_schema(tmp_path):
    perf = build_session(session_log(), "Emma", 8, speaker=ToneSpeaker(), out_dir=tmp_path)
    path = write_session(perf, tmp_path)
    again = SessionPerformance.model_validate_json(path.read_text(encoding="utf-8"))
    assert again == perf and again.format == PERFORMANCE_FORMAT
    assert all((tmp_path / t.audio).exists() for t in again.turns)
    assert set(json_schema()["properties"]) >= {"format", "child", "turns"}


def test_export_avatar_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    log_dir = tmp_path / "logs"
    s, clf, _ = make_session(load_scenario(S02), seed=0, log_dir=log_dir)
    ask(s, clf, "u", C("support"))
    s.end()
    log_path = next(log_dir.glob("*.json"))
    out = tmp_path / "out"
    assert main(["export-avatar", str(log_path), "-o", str(out), "--voice", "--speaker", "tone"]) == 0
    perf = json.loads((out / "performance.json").read_text(encoding="utf-8"))
    assert perf["child"] == {"name": "Emma", "age": 8} and perf["turns"][0]["timing"] == "audio"
    assert (out / "turn_001.wav").exists()
    assert main(["export-avatar", str(log_path), "-o", str(tmp_path / "txt")]) == 0
    assert json.loads((tmp_path / "txt" / "performance.json").read_text())["turns"][0]["timing"] == "estimated"


def test_avatar_server_refuses_a_folder_without_a_performance(tmp_path, capsys):
    assert main(["avatar", str(tmp_path)]) == 2
    assert "performance.json" in capsys.readouterr().err


def test_avatar_client_files_are_present_and_parse():
    import shutil
    import subprocess
    scripts = ["main.js", "figure.js", "cues.js", "room.js", "debug.js", "coaching.js"]
    files = ["index.html", *scripts]
    assert all((ROOT / "avatar" / f).exists() for f in files)
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent : syntaxe JS non vérifiée")
    for f in scripts:
        src = (ROOT / "avatar" / f).read_text(encoding="utf-8")
        r = subprocess.run([node, "--input-type=module", "--check"], input=src, text=True, capture_output=True)
        assert r.returncode == 0, (f, r.stderr)


def test_debug_map_is_exported_beside_the_contract_not_inside(tmp_path, monkeypatch):
    import xml.etree.ElementTree as ET
    monkeypatch.chdir(ROOT)
    log_dir = tmp_path / "logs"
    s, clf, _ = make_session(s08(1.0, reluctance=0.0), seed=4, log_dir=log_dir)
    for i, c in enumerate([C("support"), C("invitation", phase_hints=["transition"]),
                           C("option_posing", "d_bras", suggested_proposition="bras")]):
        ask(s, clf, f"u{i}", c)
    s.end()
    log_path = next(log_dir.glob("*.json"))
    plain, debug = tmp_path / "plain", tmp_path / "debug"
    assert main(["export-avatar", str(log_path), "-o", str(plain)]) == 0
    assert main(["export-avatar", str(log_path), "-o", str(debug), "--debug-map"]) == 0
    # the contract is the same with or without the map
    assert (plain / "performance.json").read_text() == (debug / "performance.json").read_text()
    assert not (plain / "debug").exists()
    index = json.loads((debug / "debug" / "maps.json").read_text())
    assert list(index) == ["1", "2", "3"] and all(len(v) == 3 for v in index.values())
    last = (debug / "debug" / index["3"][2]).read_text(encoding="utf-8")
    ET.fromstring(last)
    assert "class='n det on" in last and "Dissimulation" in last  # the lie's path lights up on the map
    first = (debug / "debug" / index["3"][0]).read_text(encoding="utf-8")
    assert "class='n core on" not in first  # step 1: the decision is not taken yet
