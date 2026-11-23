"""STT and turn-taking (ADR 0002): interruptions, units not said, metrics, voice conversation."""

import sys
from pathlib import Path

import pytest
from doubles import C, ask, make_session

from nichd_sim.delivery import Delivery, plan_speech
from nichd_sim.replay import find_scenario, replay
from nichd_sim.scenario import load_scenario
from nichd_sim.session import BargeIn, TurnTiming
from nichd_sim.voice import Audio, ToneSpeaker, VoiceError, render_speech
from nichd_sim.voice.conversation import VoiceConversation, barge_in_at
from nichd_sim.voice.listener import Transcript, WhisperListener, Word

ROOT = Path(__file__).resolve().parent.parent
S02 = ROOT / "scenarios" / "s02_violences_maison.yaml"
SR = 16000


def open_s02(seed=0):
    sc = load_scenario(S02)
    sc = sc.model_copy(update={"child_profile": sc.child_profile.model_copy(update={"reluctance": 0.0})})
    return make_session(sc, seed=seed)


# -- where an interruption falls ---------------------------------------------------------


def _reply():
    d = Delivery(onset_ms=1500, pauses_ms=[1000], fillers=2)
    plan = plan_speech("C'était à la maison, dans la cuisine. J'avais renversé mon verre de jus d'orange.", d)
    return render_speech(plan, ToneSpeaker(sample_rate=SR), d)


def _span(reply, text):
    return next(s for s in reply.timeline if s.text == text)


def test_interrupting_the_initial_silence_or_filler_is_an_onset_barge_in():
    r = _reply()
    assert barge_in_at(r, 500).during == "onset"
    filler = _span(r, "euh…")
    b = barge_in_at(r, (filler.start_ms + filler.end_ms) // 2)
    assert b.during == "onset" and b.heard_text == ""


def test_interrupting_a_pause_keeps_what_was_said():
    r = _reply()
    first = _span(r, "C'était à la maison, dans la cuisine.")
    b = barge_in_at(r, first.end_ms + 300)
    assert b.during == "pause"
    assert b.heard_text == "C'était à la maison, dans la cuisine."


def test_interrupting_mid_sentence_keeps_the_words_already_said():
    r = _reply()
    second = _span(r, "J'avais renversé mon verre de jus d'orange.")
    b = barge_in_at(r, second.start_ms + (second.end_ms - second.start_ms) // 3)
    assert b.during == "speech"
    assert b.heard_text.startswith("C'était à la maison, dans la cuisine. J'avais")
    assert "orange" not in b.heard_text


# -- the session takes back what was not said ----------------------------------------------


def test_units_cut_off_by_an_interruption_are_not_revealed_and_come_back_later():
    s, clf, _ = open_s02()
    r = ask(s, clf, "Raconte.", C("invitation"))
    said = [u.id for u in r.decision.allowed_units]
    assert said[:2] == ["b_cuisine", "b_jus"]
    barge = BargeIn(during="speech", at_ms=2000, heard_text="C'était à la maison, dans la cuisine.")
    clf.script["Et après ?"] = C("facilitator")
    nxt = s.turn("Et après ?", timing=TurnTiming(wait_ms=-3000, barge_in=barge))
    first = s.log.turns[0]
    assert first.heard_response == barge.heard_text
    assert "b_jus" in first.unheard_units and "b_cuisine" not in first.unheard_units
    assert "b_jus" not in s.log.turns[1].state_before.revealed
    told_later = [u.id for u in nxt.decision.allowed_units]
    for i in range(6):
        told_later += [u.id for u in ask(s, clf, f"Raconte {i}", C("invitation")).decision.allowed_units]
    assert "b_jus" in told_later


def test_interrupted_reply_is_shortened_in_the_history():
    s, clf, real = open_s02()
    ask(s, clf, "Raconte.", C("invitation"))
    clf.script["Et après ?"] = C("facilitator")
    barge = BargeIn(during="pause", at_ms=2000, heard_text="C'était à la maison.")
    s.turn("Et après ?", timing=TurnTiming(wait_ms=-2000, barge_in=barge))
    history = real.calls[-1][2]
    assert ("child", "C'était à la maison. —") in history


def test_recall_metric_ignores_units_that_were_cut():
    s, clf, _ = open_s02()
    said = [u.id for u in ask(s, clf, "Raconte.", C("invitation")).decision.allowed_units]
    clf.script["Hmm."] = C("support")
    s.turn("Hmm.", timing=TurnTiming(wait_ms=-4000, barge_in=BargeIn(during="onset", at_ms=200, heard_text="")))
    m = s.end().feedback.metrics
    assert m.accurate_info_recall.revealed == 0
    assert m.turn_taking.units_cut == said
    assert m.turn_taking.interruptions == {"onset": 1}


def test_turn_taking_metrics():
    s, clf, _ = open_s02()
    ask(s, clf, "u0", C("invitation"))
    onset = s.log.turns[-1].decision.delivery.onset_ms
    for i, timing in enumerate([
        TurnTiming(wait_ms=800),
        TurnTiming(wait_ms=1200),
        TurnTiming(wait_ms=-500, barge_in=BargeIn(during="speech", at_ms=3000, heard_text="C'était")),
    ]):
        clf.script[f"t{i}"] = C("invitation")
        s.turn(f"t{i}", timing=timing)
    tt = s.end().feedback.metrics.turn_taking
    assert tt.timed_turns == 3
    assert tt.median_wait_ms == 1000
    assert tt.interruptions == {"speech": 1}
    assert tt.hesitations <= 3 and tt.hesitations_respected == tt.hesitations
    assert onset > 0


def test_text_sessions_have_no_turn_taking_metrics():
    s, clf, _ = make_session()
    ask(s, clf, "Raconte.", C("invitation"))
    assert s.end().feedback.metrics.turn_taking is None


def test_voice_session_with_interruptions_replays_identically(monkeypatch):
    monkeypatch.chdir(ROOT)
    s, clf, _ = make_session(load_scenario(S02), seed=2)
    ask(s, clf, "u0", C("invitation", phase_hints=["transition"]))
    ask(s, clf, "u1", C("invitation"))
    clf.script["u2"] = C("facilitator")
    s.turn("u2", timing=TurnTiming(wait_ms=-1000, barge_in=BargeIn(during="speech", at_ms=2500, heard_text="C'était")))
    clf.script["u3"] = C("invitation")
    s.turn("u3", timing=TurnTiming(wait_ms=900))
    log = s.end()
    assert replay(log, find_scenario(log)).identical


# -- voice conversation ---------------------------------------------------------------------


class FakeListener:
    """Hears a fixed text; speech starts `lead_ms` into the recording."""

    def __init__(self, text="Dis-moi tout.", lead_ms=200):
        self.text, self.lead_ms = text, lead_ms
        self.prompts = []

    def transcribe(self, audio, *, prompt=None):
        self.prompts.append(prompt)
        return Transcript(self.text, [Word(self.text, self.lead_ms, audio.duration_ms - 100)])


def _learner(ms=1500):
    a = Audio.silence(SR, 200)
    a.extend(ToneSpeaker(sample_rate=SR, pitch_hz=140).synthesize("x" * (ms // 55)))
    return a


def test_conversation_measures_waits_and_detects_interruptions():
    s, _, _ = open_s02()
    s.classifier = type("K", (), {"classify": lambda self, u, ctx: C("invitation")})()
    conv = VoiceConversation(s, ToneSpeaker(sample_rate=SR), FakeListener(lead_ms=200))
    first = conv.exchange(_learner(), after_ms=0)
    assert first.timing.barge_in is None and first.timing.wait_ms == 200
    second = conv.exchange(_learner(), after_ms=600)
    assert second.timing.wait_ms == 800 and second.timing.barge_in is None
    child_ms = second.child.audio.duration_ms
    third = conv.exchange(_learner(), after_ms=-(child_ms - 300))  # starts during the onset silence
    assert third.timing.barge_in.during == "onset"
    assert s.log.turns[1].heard_response == ""
    assert [e.speaker for e in conv.events] == ["learner", "child"] * 3
    assert conv.events[3].text.endswith("—")  # the interrupted child reply
    assert conv.track.duration_ms >= conv.events[-1].end_ms


def test_conversation_gives_the_child_last_words_as_stt_context():
    s, _, _ = open_s02()
    s.classifier = type("K", (), {"classify": lambda self, u, ctx: C("invitation")})()
    listener = FakeListener()
    conv = VoiceConversation(s, ToneSpeaker(sample_rate=SR), listener)
    conv.exchange(_learner())
    conv.exchange(_learner())
    assert listener.prompts[0] is None and listener.prompts[1] == s.log.turns[0].response


def test_empty_recording_is_refused():
    s, _, _ = open_s02()
    conv = VoiceConversation(s, ToneSpeaker(sample_rate=SR), FakeListener(text=""))
    with pytest.raises(ValueError, match="aucune parole"):
        conv.exchange(_learner())


# -- Whisper listener -----------------------------------------------------------------------

FAKE_WHISPER = r'''
import json, sys
for line in sys.stdin:
    req = json.loads(line)
    if req.get("prompt") == "boom":
        print(json.dumps({"error": "RuntimeError: boom"}), flush=True); continue
    print(json.dumps({"text": "Dis-moi tout.", "words": [["Dis-moi", 300, 650], ["tout.", 650, 900]]}), flush=True)
'''


def test_whisper_listener_protocol(tmp_path):
    script = tmp_path / "w.py"
    script.write_text(FAKE_WHISPER)
    with WhisperListener(command=[sys.executable, str(script)]) as li:
        t = li.transcribe(Audio.silence(SR, 1000))
        assert t.text == "Dis-moi tout." and (t.speech_start_ms, t.speech_end_ms) == (300, 900)
        with pytest.raises(VoiceError, match="boom"):
            li.transcribe(Audio.silence(SR, 100), prompt="boom")


VOICE_ENV = ROOT / "experiments" / "voices" / ".envs" / "kokoro" / "bin" / "python"


@pytest.mark.skipif(not VOICE_ENV.exists(), reason="environnement voix non installé (experiments/voices)")
def test_real_whisper_hears_the_adult_kokoro_voice():
    from nichd_sim.voice import KokoroSpeaker

    with KokoroSpeaker(child=False, python=VOICE_ENV) as sp, WhisperListener(python=VOICE_ENV) as li:
        audio = Audio.silence(24000, 600)
        audio.extend(sp.synthesize("Raconte-moi tout ce qui s'est passé."))
        t = li.transcribe(audio)
    assert "raconte" in t.text.lower() and "passé" in t.text.lower()
    start, _ = audio.voiced_bounds()
    assert 600 <= start <= 1000  # 600 ms of silence + the TTS's own lead-in
    assert abs(t.speech_start_ms - start) < 600  # Whisper's word timing: only roughly right


def test_voiced_bounds_find_the_speech_in_a_recording():
    a = Audio.silence(SR, 700)
    a.extend(ToneSpeaker(sample_rate=SR).synthesize("bonjour toi"))
    a.extend(Audio.silence(SR, 500))
    start, end = a.voiced_bounds()
    assert 690 <= start <= 720
    assert abs((a.duration_ms - 500) - end) <= 30
    assert Audio.silence(SR, 500).voiced_bounds() is None


def test_voiced_bounds_resist_noise():
    """Voice evaluation N4: without a noise floor, noise at 10 dB SNR counted as speech from frame 0."""
    import math
    import random
    from array import array

    rng = random.Random(0)
    a = Audio.silence(SR, 400)
    a.extend(ToneSpeaker(sample_rate=SR).synthesize("dis-moi tout"))
    a.extend(Audio.silence(SR, 300))
    rms = math.sqrt(sum(s * s for s in a.samples if abs(s) > 300) / sum(1 for s in a.samples if abs(s) > 300))
    sigma = rms / 10 ** (10 / 20)
    noisy = Audio(SR, array("h", (max(-32768, min(32767, int(s + rng.gauss(0, sigma)))) for s in a.samples)))
    start, _ = noisy.voiced_bounds()
    assert abs(start - 400) <= 60
    click = Audio.silence(SR, 1000)
    click.samples[8000] = 20000  # an isolated click is not speech
    assert click.voiced_bounds() is None


def test_a_long_silence_lets_the_child_go_on_before_the_learner_speaks():
    """Plan lot 5 (A12): past wait_turn_ms, the session plays a wait turn first."""
    went_on = 0
    for seed in range(12):
        sc = load_scenario(S02)
        sc = sc.model_copy(update={"child_profile": sc.child_profile.model_copy(update={"reluctance": 0.0})})
        s, _, _ = make_session(sc, seed=seed, dynamics=True)
        s.classifier = type("K", (), {"classify": lambda self, u, ctx: C("invitation")})()
        conv = VoiceConversation(s, ToneSpeaker(sample_rate=SR), FakeListener(lead_ms=200))
        conv.exchange(_learner(), after_ms=0)
        short = conv.exchange(_learner(), after_ms=600)
        assert short.waited is None
        long = conv.exchange(_learner(), after_ms=s.params["wait_turn_ms"] + 1000)
        assert long.waited is not None and s.log.turns[-2].kind == "wait"
        if long.waited.decision.speech_act != "silence":
            went_on += 1
            assert [e.speaker for e in conv.events][-3:] == ["child", "learner", "child"]
            assert long.timing.wait_ms == 1200  # the rest of the silence, after the continuation
    assert went_on > 0
