"""Automatic classification (#4): LLM classifier contract, fallbacks, logging."""

import json

from doubles import S01, RecordingRealizer
from nichd_sim.classification import OUT_OF_SCENARIO, QuestionType
from nichd_sim.classifiers.llm import LLMClassifier, Skill
from nichd_sim.engine import SpeechAct
from nichd_sim.llm import ChatResult, LLMError
from nichd_sim.scenario import load_scenario
from nichd_sim.session import Session


class FakeChat:
    model = "fake-classifier"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, *, temperature, seed=None, think=False, format=None):
        self.calls.append({"messages": messages, "temperature": temperature, "format": format, "think": think})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return ChatResult(content=content, meta={"latency_s": 0.01, "model": self.model})


def label(type, target=None, phase="substantive", **kw):
    return {"type": type, "inner_type": kw.get("inner_type"), "target": target,
            "suggested_proposition": kw.get("prop"), "options": kw.get("options"), "phase_hint": phase}


def session(chat, **kw):
    return Session(load_scenario(S01), LLMClassifier(chat), RecordingRealizer(), **kw)


def test_free_utterance_is_classified_and_drives_the_engine():
    chat = FakeChat(label("invitation"), label("directive", "d_pousse"))
    s = session(chat)
    r = s.turn("Dis-moi tout ce qui s'est passé au parc.")
    assert r.classification.type == QuestionType.INVITATION
    assert r.decision.speech_act == SpeechAct.ANSWER
    r = s.turn("Qui a poussé qui ?")
    assert r.classification.target == "d_pousse"
    assert [u.id for u in r.decision.allowed_units] == ["d_pousse"]


def test_request_uses_skill_schema_temperature_zero_and_scenario_catalog():
    chat = FakeChat(label("invitation"))
    s = session(chat)
    s.turn("Raconte-moi.")
    call = chat.calls[0]
    assert call["temperature"] == 0 and call["think"] is False
    assert call["format"] == Skill.load().schema
    system, user = call["messages"][0]["content"], call["messages"][1]["content"]
    assert "cued_invitation" in system and "Exemples" in system
    assert "d_pousse" in user and "Raconte-moi." in user


def test_invalid_json_falls_back_to_other_and_is_logged():
    chat = FakeChat("pas du json")
    s = session(chat)
    r = s.turn("Raconte.")
    assert r.classification.type == QuestionType.OTHER
    assert r.decision.speech_act == SpeechAct.CONFUSION
    meta = s.log.turns[0].classification.meta
    assert meta["error"].startswith("invalid_output") and meta["raw"] == "pas du json"


def test_schema_violation_falls_back_to_other():
    chat = FakeChat({"type": "question_bizarre", "phase_hint": "substantive"})
    r = session(chat).turn("Raconte.")
    assert r.classification.type == QuestionType.OTHER and "error" in r.classification.meta


def test_llm_unreachable_falls_back_to_other():
    chat = FakeChat(LLMError("down"))
    r = session(chat).turn("Raconte.")
    assert r.classification.type == QuestionType.OTHER
    assert r.classification.meta["error"].startswith("llm_error")


def test_unknown_target_becomes_out_of_scenario():
    chat = FakeChat(label("directive", "u_inexistante"))
    r = session(chat).turn("Il avait quelle voiture ?")
    assert r.classification.target == OUT_OF_SCENARIO
    assert r.decision.speech_act == SpeechAct.DONT_KNOW
    assert r.classification.meta["unknown_target"] == "u_inexistante"


def test_compound_exposes_inner_type_and_phase_hint():
    chat = FakeChat(label("compound", "d_pousse", inner_type="directive", phase="substantive"))
    r = session(chat).turn("Il était où et qui a poussé ?")
    assert r.classification.inner_type == QuestionType.DIRECTIVE
    assert r.classification.phase_hints == ["substantive"]


def test_skill_version_and_latencies_are_logged(tmp_path):
    chat = FakeChat(label("invitation"))
    s = session(chat, log_dir=tmp_path)
    s.turn("Raconte.")
    s.end()
    data = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert data["components"]["skill_version"] == Skill.load().version
    assert data["components"]["classifier"] == "LLMClassifier(fake-classifier)"
    assert set(data["turns"][0]["latency_s"]) == {"classification", "realization", "total"}
    assert data["turns"][0]["classification"]["meta"]["latency_s"] == 0.01


def test_skill_examples_conform_to_schema_and_typology():
    skill = Skill.load()
    ids = {u["id"] for u in skill.example_catalog}
    types = set(skill.schema["properties"]["type"]["enum"])
    assert len(skill.examples) >= 40
    for ex in skill.examples:
        lab = ex["label"]
        assert set(lab) == set(skill.schema["required"]), ex["id"]
        assert lab["type"] in types
        assert lab["target"] in ids | {OUT_OF_SCENARIO, None}, ex["id"]
        assert set(ex["already_said"]) <= ids
    assert types <= {ex["label"]["type"] for ex in skill.examples}
