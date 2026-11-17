"""Qwen3-TTS speaker (voice v2): voice bank, worker protocol, native rendering with the engine's pauses."""

import json
import sys

import pytest

from nichd_sim.delivery import ChunkKind, Delivery, plan_speech
from nichd_sim.evaluation import load_scenarios
from nichd_sim.voice import (
    QwenSpeaker,
    SpeakerError,
    make_speaker,
    render_speech,
    voice_bank,
    voice_for,
)
from nichd_sim.voice.qwen_speaker import BANK, DEFAULT_VOICE
from nichd_sim.voice.render import NATIVE_STYLE, style_for

FAKE_WORKER = r'''
import base64, json, math, sys
from array import array
for line in sys.stdin:
    req = json.loads(line)
    if req["text"] == "boom":
        print(json.dumps({"error": "ValueError: boom"}), flush=True); continue
    sr, out = 24000, array("h")
    for k, piece in enumerate(p for p in req["text"].split("…") if p.strip()):
        if k:
            out.extend([0] * (sr * 250 // 1000))  # the voice's own pause: 250 ms
        n = sr * (45 * len(piece) + req["seed"] % 7) // 1000
        out.extend(int(6000 * math.sin(2 * math.pi * 300 * i / sr)) for i in range(n))
    print(json.dumps({"sample_rate": sr, "audio": base64.b64encode(out.tobytes()).decode(), "echo": req}), flush=True)
'''


@pytest.fixture
def fake_qwen(tmp_path):
    script = tmp_path / "worker.py"
    script.write_text(FAKE_WORKER)
    sp = QwenSpeaker("garcon_10_12", command=[sys.executable, str(script)])
    yield sp
    sp.close()


def test_the_bank_has_one_voice_per_gender_and_age_band():
    bank = voice_bank()
    for gender in ("fille", "garcon"):
        for band in ("4_6", "7_9", "10_12"):
            entry = bank[f"{gender}_{band}"]
            assert (BANK / entry["file"]).exists() and entry["ref_text"].strip()
            assert entry["gender"] == gender and entry["band"] == band
    assert DEFAULT_VOICE in bank


def test_every_scenario_child_gets_its_own_voice():
    for sc in load_scenarios("scenarios").values():
        p = sc.child_profile
        assert p.voice is not None, sc.id
        assert voice_for(p) == f"{p.voice.value}_{p.age_band.value}", sc.id


def test_voice_defaults_to_the_validated_girl_voice():
    assert voice_for(None) == DEFAULT_VOICE
    sc = next(iter(load_scenarios("scenarios").values()))
    no_voice = sc.child_profile.model_copy(update={"voice": None})
    assert voice_for(no_voice).startswith("fille_")


def test_unknown_voice_is_a_clear_error():
    with pytest.raises(SpeakerError, match="voix inconnue"):
        QwenSpeaker("robot", command=[sys.executable, "-c", "pass"])


def test_speaker_sends_the_reference_and_a_replayable_seed(fake_qwen):
    a = fake_qwen.synthesize("Je sais pas.")
    b = fake_qwen.synthesize("Je sais pas.")
    assert a.samples == b.samples and a.sample_rate == 24000
    req = fake_qwen._worker.request({"text": "x", "seed": 0, **fake_qwen._ref})["echo"]
    assert req["ref_audio"].endswith(voice_bank()["garcon_10_12"]["file"])


def test_worker_errors_are_reported_and_the_worker_keeps_serving(fake_qwen):
    with pytest.raises(SpeakerError, match="boom"):
        fake_qwen.synthesize("boom")
    assert fake_qwen.synthesize("Oui.").samples


def test_qwen_renders_natively_with_the_engines_pauses(fake_qwen):
    assert style_for(fake_qwen) == NATIVE_STYLE
    d = Delivery(onset_ms=1200, pauses_ms=[800], fillers=1)
    plan = plan_speech("il m'a attrapé le bras et après il est parti dans le salon", d)
    r = render_speech(plan, fake_qwen, d)
    assert r.onset_ms == 1200
    planned = [c.ms for c in plan[1:] if c.kind == ChunkKind.SILENCE]
    rendered = [s.end_ms - s.start_ms for s in r.timeline[1:] if s.kind == ChunkKind.SILENCE]
    assert rendered == planned  # the voice paused 250 ms; the engine wanted 800 ms (and the filler gap)


def test_make_speaker_picks_the_childs_voice(monkeypatch):
    monkeypatch.setenv("NICHD_QWEN_PYTHON", sys.executable)  # the worker is only started on first request
    sc = next(s for s in load_scenarios("scenarios").values() if s.child_profile.name == "Lucas")
    sp = make_speaker("qwen", sc.child_profile)
    assert isinstance(sp, QwenSpeaker) and sp.voice == "garcon_10_12"


def test_bank_metadata_is_valid_json():
    data = json.loads((BANK / "voices.json").read_text(encoding="utf-8"))
    assert all("instruct" in v and "Qwen3-TTS" in v.get("source", "") for v in data.values())
