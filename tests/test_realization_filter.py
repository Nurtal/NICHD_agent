"""Child voice and output filter (#3): regeneration, fallback, prompt hygiene."""

from doubles import S01, C, ScriptedClassifier, ask
from nichd_sim.llm import ChatResult
from nichd_sim.realization import LLMRealizer, Realization
from nichd_sim.scenario import load_scenario
from nichd_sim.session import Session


class ScriptedRealizer:
    """Returns the given texts in order, one per call."""

    def __init__(self, *texts):
        self.texts = list(texts)
        self.attempts = []

    def realize(self, decision, profile, history, attempt=0):
        self.attempts.append(attempt)
        return Realization(text=self.texts.pop(0), prompt=f"prompt#{attempt}")


class FakeChat:
    model = "fake-model"

    def __init__(self, reply="Euh… y avait ma mamie."):
        self.reply = reply
        self.calls = []

    def chat(self, messages, *, temperature, seed=None, think=False, format=None):
        self.calls.append({"messages": messages, "temperature": temperature, "seed": seed, "think": think})
        return ChatResult(content=self.reply, meta={"seed": seed, "latency_s": 0.0})


def session_with(realizer, **kw):
    clf = ScriptedClassifier()
    return Session(load_scenario(S01), clf, realizer, **kw), clf


def test_clean_response_passes_through():
    s, clf = session_with(ScriptedRealizer("Y avait ma mamie. On était au parc."))
    r = ask(s, clf, "Raconte.", C("invitation"))
    assert r.response == "Y avait ma mamie. On était au parc."
    assert not r.fallback_used and len(s.log.turns[0].attempts) == 1


def test_leaked_anchor_triggers_one_regeneration():
    # "peur" is an anchor of a_peur, not authorized for this turn
    real = ScriptedRealizer("Y avait ma mamie et j'avais peur.", "J'étais au parc avec mamie.")
    s, clf = session_with(real)
    r = ask(s, clf, "Raconte.", C("invitation"))
    assert r.response == "J'étais au parc avec mamie."
    assert real.attempts == [0, 1]
    first = s.log.turns[0].attempts[0]
    assert not first.ok and first.leaked_units == ["a_peur"]


def test_two_failures_fall_back_to_authored_response():
    real = ScriptedRealizer("Le chien aboyait.", "Le monsieur au blouson rouge.")
    s, clf = session_with(real)
    r = ask(s, clf, "Raconte.", C("invitation"))
    assert r.fallback_used
    assert r.response == "J'étais au parc avec ma mamie. C'était au parc à côté de l'école."
    assert s.log.turns[0].fallback_used and len(s.log.turns[0].attempts) == 2


def test_forbidden_lexicon_triggers_regeneration_then_fallback():
    s, clf = session_with(ScriptedRealizer("Il était tout nu.", "Il était nu."))
    r = ask(s, clf, "Il s'est passé quoi ?", C("other"))
    assert r.fallback_used and r.response == "Hein ? Je comprends pas."
    assert s.log.turns[0].attempts[0].forbidden_terms == ["nu"]


def test_mentioning_an_already_said_fact_is_not_a_leak():
    real = ScriptedRealizer("Mamie et moi au parc.", "Le monsieur, celui de mamie au parc, il a poussé.")
    s, clf = session_with(real)
    ask(s, clf, "Raconte.", C("invitation"))  # b_mamie, b_parc said
    r = ask(s, clf, "Qui a poussé ?", C("directive", "d_pousse"))
    assert not r.fallback_used and s.log.turns[1].attempts[0].ok


def test_words_shared_with_an_allowed_fact_are_not_a_leak():
    # "Bertin" is an anchor of d_messieurs but also appears in the allowed d_tombe value
    s, clf = session_with(ScriptedRealizer("Monsieur Bertin il est tombé par terre."))
    r = ask(s, clf, "Et lui ?", C("directive", "d_tombe"))
    assert not r.fallback_used


def test_accents_and_case_do_not_hide_a_leak():
    s, clf = session_with(ScriptedRealizer("Y avait un CHIEN.", "Y avait un chien."))
    r = ask(s, clf, "Raconte.", C("invitation"))
    assert r.fallback_used


def test_llm_prompt_contains_only_allowed_facts():
    scenario = load_scenario(S01)
    chat = FakeChat()
    s, clf = session_with(LLMRealizer(chat, seed=7))
    ask(s, clf, "Raconte-moi tout.", C("invitation"))  # b_mamie, b_parc
    call = chat.calls[0]
    prompt = "\n".join(m["content"] for m in call["messages"])
    allowed = {"b_mamie", "b_parc"}
    for _, unit in scenario.all_units():
        if unit.id in allowed:
            assert unit.value in prompt
        else:
            assert unit.value not in prompt
            assert not any(a.lower() in prompt.lower() for a in unit.anchors if a not in ("école",)), unit.id
    assert call["think"] is False and call["temperature"] == 0.7
    assert len(call["messages"]) == 2
    assert "« Raconte-moi tout. »" in call["messages"][1]["content"]
    assert "5 ans" in call["messages"][0]["content"]


def test_llm_seed_is_deterministic_and_changes_on_regeneration():
    chat = FakeChat(reply="Le chien aboyait.")  # always leaks → 2 attempts
    s, clf = session_with(LLMRealizer(chat, seed=3))
    ask(s, clf, "Raconte.", C("invitation"))
    seeds = [c["seed"] for c in chat.calls]
    assert len(seeds) == 2 and seeds[0] != seeds[1]

    chat2 = FakeChat(reply="Le chien aboyait.")
    s2, clf2 = session_with(LLMRealizer(chat2, seed=3))
    ask(s2, clf2, "Raconte.", C("invitation"))
    assert [c["seed"] for c in chat2.calls] == seeds


def test_log_records_prompts_raw_responses_and_filter_verdicts():
    chat = FakeChat(reply="Y avait ma mamie, j'avais peur.")
    s, clf = session_with(LLMRealizer(chat, seed=1))
    ask(s, clf, "Raconte.", C("invitation"))
    turn = s.log.model_dump()["turns"][0]
    assert len(turn["attempts"]) == 2
    a0 = turn["attempts"][0]
    assert a0["prompt"] and a0["text"] == "Y avait ma mamie, j'avais peur."
    assert a0["ok"] is False and a0["leaked_units"] == ["a_peur"]
    assert a0["meta"]["seed"] is not None
    assert turn["fallback_used"] is True and turn["response"]
    assert s.log.components["realizer"] == "LLMRealizer(fake-model)"


def test_omitting_an_allowed_fact_triggers_regeneration():
    # d_crient is allowed but not expressed in the first attempt
    real = ScriptedRealizer(
        "Y avait deux messieurs.",  # turn 1
        "Y avait deux messieurs.",  # turn 2, attempt 1: omits d_crient
        "Y avait deux messieurs, ils criaient fort.",  # turn 2, attempt 2
    )
    s, clf = session_with(real)
    ask(s, clf, "Qui ?", C("directive", "d_messieurs"))
    r = ask(s, clf, "Et ?", C("directive", "d_crient"))
    assert r.response == "Y avait deux messieurs, ils criaient fort."
    assert s.log.turns[1].attempts[0].missing_units == ["d_crient"]


def test_inflected_anchor_counts_as_expressed():
    s, clf = session_with(ScriptedRealizer("Il le poussait, le monsieur."))
    r = ask(s, clf, "Il a fait quoi ?", C("directive", "d_pousse"))
    assert not r.fallback_used and s.log.turns[0].attempts[0].ok


def test_inflected_form_of_a_forbidden_anchor_is_a_leak():
    # "crié" is an inflection of d_crient's anchor "crier"
    s, clf = session_with(ScriptedRealizer("Mamie a crié.", "Mamie a téléphoné."))
    r = ask(s, clf, "Et mamie ?", C("directive", "a_telephone"))
    assert s.log.turns[0].attempts[0].leaked_units == ["d_crient"]
    assert r.response == "Mamie a téléphoné."


def test_empty_response_is_rejected():
    s, clf = session_with(ScriptedRealizer("", "  "))
    r = ask(s, clf, "Il avait quelle voiture ?", C("directive", "out_of_scenario"))
    assert r.fallback_used and r.response == "Je sais pas."
    assert s.log.turns[0].attempts[0].empty


def test_content_free_act_that_runs_on_is_rejected():
    long = "et après j'ai dit à la maîtresse que c'était un accident avec la chaise de la cuisine"
    s, clf = session_with(ScriptedRealizer(long, "Je sais pas."))
    r = ask(s, clf, "Il avait quelle voiture ?", C("directive", "out_of_scenario"))
    assert r.response == "Je sais pas."
    assert s.log.turns[0].attempts[0].too_long


def test_regeneration_is_stricter_and_cooler():
    chat = FakeChat(reply="Le chien aboyait.")  # always leaks → 2 attempts
    s, clf = session_with(LLMRealizer(chat, seed=3))
    ask(s, clf, "Raconte.", C("invitation"))
    first, second = chat.calls
    assert first["temperature"] == 0.7 and second["temperature"] == 0.3
    assert "refusée" in second["messages"][0]["content"] and "refusée" not in first["messages"][0]["content"]


def test_refusal_prompt_asks_for_a_plain_no():
    """A rejected suggestion was voiced « Non, c'est tout » (closing formula) instead of a plain no."""
    from nichd_sim.engine import Decision, SpeechAct
    from nichd_sim.realization import build_system_prompt

    prompt = build_system_prompt(Decision(speech_act=SpeechAct.DENY, reason="suggestion fausse → refus"),
                                 load_scenario(S01).child_profile)
    assert "simplement non" in prompt and "c'est tout" not in prompt
