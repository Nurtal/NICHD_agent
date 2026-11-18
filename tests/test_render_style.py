"""Optional render styles (voice screening v2): room tone, longer fades, native rendering."""

from nichd_sim.delivery import ChunkKind, Delivery, plan_speech
from nichd_sim.voice import ToneSpeaker
from nichd_sim.voice.render import (
    DEFAULT_STYLE, NATIVE_STYLE, NATURAL_STYLE, PAUSE_MARK, native_text, render_speech, room_tone, speech_spans,
)

TEXT = "il m'a attrapé le bras et après il est parti dans le salon"
DELIVERY = Delivery(onset_ms=900, pauses_ms=[600], fillers=1)


def _plan():
    return plan_speech(TEXT, DELIVERY)


def test_default_style_is_the_original_assembly():
    a = render_speech(_plan(), ToneSpeaker(), DELIVERY)
    b = render_speech(_plan(), ToneSpeaker(), DELIVERY, DEFAULT_STYLE)
    assert a.audio.samples == b.audio.samples and a.timeline == b.timeline
    first = a.timeline[0]
    assert first.kind == ChunkKind.SILENCE
    n = round(a.audio.sample_rate * first.end_ms / 1000)
    assert max(abs(x) for x in a.audio.samples[:n]) == 0  # digital silence


def test_room_tone_fills_the_silences_quietly():
    r = render_speech(_plan(), ToneSpeaker(), DELIVERY, NATURAL_STYLE)
    n = round(r.audio.sample_rate * r.timeline[0].end_ms / 1000)
    onset = r.audio.samples[:n]
    peak = max(abs(x) for x in onset)
    assert 0 < peak < 32767 * 10 ** (-40 / 20)  # audible bed, far below speech
    assert room_tone(24000, 500, -58).samples == room_tone(24000, 500, -58).samples  # deterministic


def test_native_text_writes_the_pauses():
    text = native_text(_plan())
    assert text.startswith("euh…") and PAUSE_MARK in text.split("euh…", 1)[1]
    assert "  " not in text


def test_native_rendering_measures_its_timeline():
    r = render_speech(_plan(), ToneSpeaker(), DELIVERY, NATIVE_STYLE)
    tl = r.timeline
    assert tl[0].kind == ChunkKind.SILENCE and tl[0].end_ms == DELIVERY.onset_ms
    assert any(s.kind == ChunkKind.SPEECH for s in tl)
    for a, b in zip(tl, tl[1:]):
        assert a.end_ms == b.start_ms
    assert tl[-1].end_ms == r.audio.duration_ms


def test_speech_spans_split_at_real_pauses():
    sp = ToneSpeaker()
    a = sp.synthesize("bonjour toi")
    from nichd_sim.voice import Audio
    joined = Audio(sp.sample_rate)
    joined.extend(a)
    joined.extend(Audio.silence(sp.sample_rate, 400))
    joined.extend(a)
    spans = speech_spans(joined)
    assert len(spans) == 2 and spans[1][0] - spans[0][1] >= 300
