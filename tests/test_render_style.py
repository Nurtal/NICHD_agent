"""Optional render styles (voice screening v2): room tone, longer fades, native rendering."""

from nichd_sim.delivery import ChunkKind, Delivery, plan_speech
from nichd_sim.voice import ToneSpeaker
from nichd_sim.voice.render import (
    DEFAULT_STYLE,
    NATIVE_STYLE,
    NATURAL_STYLE,
    PAUSE_MARK,
    native_text,
    render_speech,
    room_tone,
    speech_spans,
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


class _SpokenPauses:
    """A native TTS stand-in: speaks « … » as a 300 ms pause, whatever the plan wanted."""

    sample_rate = 24000

    def synthesize(self, text, *, rate=1.0):
        from nichd_sim.voice import Audio
        tone = ToneSpeaker(sample_rate=self.sample_rate)
        out = Audio(self.sample_rate)
        for k, piece in enumerate(p for p in text.split(PAUSE_MARK) if p.strip()):
            if k:
                out.extend(Audio.silence(self.sample_rate, 300))
            out.extend(tone.synthesize(piece, rate=rate))
        return out


def test_native_pauses_are_retimed_to_the_plan():
    """The engine decides how long the child pauses; the native voice only says the words."""
    plan = _plan()
    r = render_speech(plan, _SpokenPauses(), DELIVERY, NATIVE_STYLE)
    planned = [c.ms for c in plan[1:] if c.kind == ChunkKind.SILENCE]
    rendered = [s.end_ms - s.start_ms for s in r.timeline[1:] if s.kind == ChunkKind.SILENCE]
    assert rendered == planned  # 600 ms stays 600 ms although the voice paused 300 ms
    assert r.timeline[0].end_ms == DELIVERY.onset_ms
    assert [s.text for s in r.timeline if s.kind == ChunkKind.SPEECH] == [c.text for c in plan if c.kind == ChunkKind.SPEECH]
    for a, b in zip(r.timeline, r.timeline[1:]):
        assert a.end_ms == b.start_ms
    assert abs(r.timeline[-1].end_ms - r.audio.duration_ms) <= 1


def test_native_keeps_the_voice_when_pauses_do_not_match():
    from nichd_sim.voice import Audio

    class OneBreath(_SpokenPauses):
        def synthesize(self, text, *, rate=1.0):  # no pause at all
            return ToneSpeaker(sample_rate=self.sample_rate).synthesize(text.replace(PAUSE_MARK, " "), rate=rate)

    r = render_speech(_plan(), OneBreath(), DELIVERY, NATIVE_STYLE)
    assert isinstance(r.audio, Audio) and r.timeline[-1].end_ms == r.audio.duration_ms


def test_run_together_pieces_are_cut_at_the_dip_not_at_a_far_breath():
    """« euh je sais pas » said in one breath, then a breath after a pause: the planned pause goes
    after « euh » (the energy dip where the text puts it), not at the end of the reply."""
    from nichd_sim.voice import Audio

    sr = 24000
    tone = ToneSpeaker(sample_rate=sr)

    class RunTogether:
        sample_rate = sr
        native = True

        def synthesize(self, text, *, rate=1.0):
            out = Audio(sr)
            out.extend(tone.synthesize("euh…"))
            out.extend(tone.synthesize("euh…").scaled(0.1))  # a dip, never silent
            out.extend(tone.synthesize("Je sais pas."))
            out.extend(Audio.silence(sr, 200))
            out.extend(tone.synthesize("hh").scaled(0.3))  # a breath at the very end
            return out

    d = Delivery(onset_ms=500, fillers=1)
    plan = plan_speech("Je sais pas.", d)
    r = render_speech(plan, RunTogether(), d)
    speech = [s for s in r.timeline if s.kind == ChunkKind.SPEECH]
    assert [s.text for s in speech] == ["euh…", "Je sais pas."]
    filler_ms = tone.synthesize("euh…").duration_ms
    assert abs((speech[0].end_ms - speech[0].start_ms) - filler_ms) < 2 * filler_ms  # cut near « euh », not 1 s later
    planned = [c.ms for c in plan[1:] if c.kind == ChunkKind.SILENCE]
    assert [s.end_ms - s.start_ms for s in r.timeline[1:] if s.kind == ChunkKind.SILENCE] == planned
