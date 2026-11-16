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
    assert main(["render-audio", str(log), "-o", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("turn_*.wav"))) == 22
