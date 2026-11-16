"""Voice layer (ADR 0002): silences inserted exactly, TTS padding trimmed, volume, log rendering."""

from pathlib import Path

import pytest
from doubles import C, ask, make_session

from nichd_sim.cli import main
from nichd_sim.delivery import ChunkKind, Delivery, Volume, plan_speech
from nichd_sim.replay import load_log
from nichd_sim.voice import Audio, ToneSpeaker, make_speaker, render_log, render_speech

ROOT = Path(__file__).resolve().parent.parent
SR = 16000


class PaddedSpeaker(ToneSpeaker):
    """Like most TTS models: adds silence around the speech."""

    def synthesize(self, text, *, rate=1.0):
        audio = Audio.silence(self.sample_rate, 300)
        audio.extend(super().synthesize(text, rate=rate))
        audio.extend(Audio.silence(self.sample_rate, 400))
        return audio


def _leading_zeros(audio: Audio) -> int:
    return next(i for i, s in enumerate(audio.samples) if s != 0)


def test_onset_silence_is_exact_even_with_a_padded_tts():
    d = Delivery(onset_ms=1500, pauses_ms=[800], fillers=1)
    plan = plan_speech("Je suis allée dans ma chambre, et après j'ai pleuré.", d)
    r = render_speech(plan, PaddedSpeaker(sample_rate=SR), d)
    # 20 ms trim margin + the tone's own fade: the onset is within a few ms of the plan
    assert 1500 <= r.onset_ms <= 1500 + 25
    assert _leading_zeros(r.audio) == pytest.approx(SR * 1.5, abs=SR * 0.025)
    silences = [s for s in r.timeline if s.kind == ChunkKind.SILENCE]
    assert [s.end_ms - s.start_ms for s in silences] == [1500, 250, 800]


def test_timeline_covers_the_whole_audio_in_plan_order():
    d = Delivery(onset_ms=700, pauses_ms=[600, 600], fillers=2)
    plan = plan_speech("C'était dimanche soir. Maman était partie. La télé était allumée.", d)
    r = render_speech(plan, ToneSpeaker(sample_rate=SR), d)
    assert [s.kind for s in r.timeline] == [c.kind for c in plan]
    assert r.timeline[0].start_ms == 0 and r.timeline[-1].end_ms == r.audio.duration_ms
    assert all(a.end_ms == b.start_ms for a, b in zip(r.timeline, r.timeline[1:]))


def test_slower_rate_means_longer_speech():
    fast = ToneSpeaker(sample_rate=SR).synthesize("je sais pas", rate=1.0)
    slow = ToneSpeaker(sample_rate=SR).synthesize("je sais pas", rate=0.75)
    assert slow.duration_ms > fast.duration_ms


def test_low_volume_is_quieter():
    plan = plan_speech("Il m'a tapé.", None)
    loud = render_speech(plan, ToneSpeaker(sample_rate=SR), Delivery(onset_ms=0))
    quiet = render_speech(plan, ToneSpeaker(sample_rate=SR), Delivery(onset_ms=0, volume=Volume.WHISPER))
    assert max(quiet.audio.samples) < 0.5 * max(loud.audio.samples)


def test_wav_round_trip(tmp_path):
    a = ToneSpeaker(sample_rate=SR).synthesize("bonjour")
    b = Audio.read_wav(a.write_wav(tmp_path / "x.wav"))
    assert b.sample_rate == SR and b.samples == a.samples


def test_mixing_sample_rates_is_refused():
    a = Audio.silence(SR, 10)
    with pytest.raises(ValueError):
        a.extend(Audio.silence(22050, 10))


def test_unknown_speaker_is_a_clear_error():
    with pytest.raises(ValueError, match="voix inconnue"):
        make_speaker("nope")


def test_session_reply_renders_with_its_own_delivery():
    s, clf, _ = make_session()
    r = ask(s, clf, "Raconte.", C("invitation"))
    rendered = render_speech(r.speech_plan, ToneSpeaker(sample_rate=SR), r.decision.delivery)
    assert rendered.onset_ms == pytest.approx(r.decision.delivery.onset_ms, abs=25)


def test_render_log_writes_one_wav_per_turn_even_for_mvp_logs(tmp_path):
    log = load_log(ROOT / "tests" / "fixtures" / "mvp_logs" / "mvp_s01_bagarre_parc_0.json")
    paths = render_log(log, ToneSpeaker(sample_rate=SR), tmp_path)
    assert len(paths) == len(log.turns)
    assert all(p.exists() and Audio.read_wav(p).sample_rate == SR for p in paths)


def test_cli_render_audio(tmp_path, capsys):
    log = ROOT / "tests" / "fixtures" / "mvp_logs" / "mvp_s01_bagarre_parc_0.json"
    assert main(["render-audio", str(log), "-o", str(tmp_path), "--speaker", "tone"]) == 0
    assert len(list(tmp_path.glob("turn_*.wav"))) == 22


# -- Kokoro speaker (worker protocol) ------------------------------------------------

import sys as _sys

from nichd_sim.voice import KokoroSpeaker, SpeakerError

FAKE_WORKER = r'''
import base64, json, math, sys
from array import array
for line in sys.stdin:
    req = json.loads(line)
    if req["pieces"] == ["boom"]:
        print(json.dumps({"error": "ValueError: boom"}), flush=True); continue
    if req["pieces"] == ["crash"]:
        sys.stderr.write("CUDA out of memory\n"); sys.exit(3)
    out = []
    for i, p in enumerate(req["pieces"]):
        n = 24 * (40 * len(p) + req["seed"] % 7)
        out.append(base64.b64encode(array("h", (int(5000 * math.sin(i + k / 9)) for k in range(n))).tobytes()).decode())
    print(json.dumps({"sample_rate": 24000, "pieces": out, "echo": req}), flush=True)
'''


@pytest.fixture
def fake_kokoro(tmp_path):
    script = tmp_path / "worker.py"
    script.write_text(FAKE_WORKER)
    sp = KokoroSpeaker(command=[_sys.executable, str(script)])
    yield sp
    sp.close()


def test_kokoro_speaker_returns_one_audio_per_piece(fake_kokoro):
    pieces = fake_kokoro.synthesize_pieces(["euh…", "Je suis allée dans ma chambre,", "et après."], rate=0.8)
    assert len(pieces) == 3 and all(p.sample_rate == 24000 and p.samples for p in pieces)
    assert pieces[1].duration_ms > pieces[0].duration_ms


def test_kokoro_seed_depends_on_the_text_only(fake_kokoro):
    a = fake_kokoro.synthesize_pieces(["Je sais pas."])
    b = fake_kokoro.synthesize_pieces(["Je sais pas."])
    c = fake_kokoro.synthesize_pieces(["Je sais."])
    assert a[0].samples == b[0].samples
    assert len(c) == 1


def test_kokoro_worker_errors_are_reported_and_the_worker_keeps_serving(fake_kokoro):
    with pytest.raises(SpeakerError, match="boom"):
        fake_kokoro.synthesize("boom")
    assert fake_kokoro.synthesize("Oui.").samples


def test_kokoro_worker_crash_shows_its_stderr_and_restarts(fake_kokoro):
    with pytest.raises(SpeakerError, match="CUDA out of memory"):
        fake_kokoro.synthesize("crash")
    assert fake_kokoro.synthesize("Oui.").samples  # a new worker is started


def test_render_uses_one_utterance_when_the_speaker_supports_it(fake_kokoro):
    calls = []
    original = fake_kokoro.synthesize_pieces

    def spy(pieces, *, rate=1.0):
        calls.append((pieces, rate))
        return original(pieces, rate=rate)

    fake_kokoro.synthesize_pieces = spy
    d = Delivery(onset_ms=900, pauses_ms=[700], fillers=2, rate=0.8)
    plan = plan_speech("Je suis allée dans ma chambre, et après j'ai pleuré.", d)
    r = render_speech(plan, fake_kokoro, d)
    assert calls == [(["euh…", "Je suis allée dans ma chambre,", "euh…", "et après j'ai pleuré."], 0.8)]
    assert r.onset_ms == pytest.approx(900, abs=25)


def test_missing_kokoro_env_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.delenv("NICHD_KOKORO_PYTHON", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("nichd_sim.voice.kokoro_speaker.Path.exists", lambda self: False)
    with pytest.raises(SpeakerError, match="environnement Kokoro introuvable"):
        KokoroSpeaker()


KOKORO_ENV = ROOT / "experiments" / "voices" / ".envs" / "kokoro" / "bin" / "python"


@pytest.mark.skipif(not KOKORO_ENV.exists(), reason="environnement Kokoro non installé (experiments/voices)")
def test_real_kokoro_child_voice_end_to_end():
    d = Delivery(onset_ms=1200, pauses_ms=[800], fillers=1, rate=0.9)
    plan = plan_speech("Je suis allée dans ma chambre, et après j'ai pleuré.", d)
    with KokoroSpeaker(python=KOKORO_ENV) as sp:
        a = render_speech(plan, sp, d)
        b = render_speech(plan, sp, d)
    assert a.audio.sample_rate == 24000
    assert a.onset_ms == pytest.approx(1200, abs=25)
    assert a.audio.samples == b.audio.samples  # replayable audio
    speech = [s for s in a.timeline if s.kind == ChunkKind.SPEECH]
    assert len(speech) == 3 and all(s.end_ms - s.start_ms > 150 for s in speech)
