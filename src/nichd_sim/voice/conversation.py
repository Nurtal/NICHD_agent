"""Voice conversation: learner audio → STT → session → TTS, with turn-taking and one audio track.

Timing convention: each learner recording is placed `after_ms` after the END of the child's previous
reply audio (negative: the recording starts while the child is still on — possibly an interruption).
The learner's real speech start is the recording start + the first word Whisper hears.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nichd_sim.delivery import FILLER, ChunkKind
from nichd_sim.engine import SpeechAct
from nichd_sim.session import BargeIn, Session, TurnResult, TurnTiming
from nichd_sim.voice.audio import Audio
from nichd_sim.voice.listener import Listener, Transcript
from nichd_sim.voice.render import RenderedSpeech, render_speech
from nichd_sim.voice.speaker import Speaker

CHILD_REACTION_MS = 250
"""Once interrupted, the child stops talking after this delay."""


def barge_in_at(reply: RenderedSpeech, at_ms: int) -> BargeIn:
    """What the interruption at `at_ms` (offset in the child's reply audio) cut off."""
    speech = [s for s in reply.timeline if s.kind == ChunkKind.SPEECH and s.text != FILLER]
    if not speech or at_ms < speech[0].start_ms:
        during = "onset"
    else:
        current = next((s for s in reply.timeline if s.start_ms <= at_ms < s.end_ms), None)
        is_talking = current is not None and current.kind == ChunkKind.SPEECH and current.text != FILLER
        during = "speech" if is_talking else "pause"
    heard = []
    for s in speech:
        if s.end_ms <= at_ms:
            heard.append(s.text)
        elif s.start_ms < at_ms:  # cut mid-piece: keep the words already spoken (proportional)
            words = s.text.split()
            n = int(len(words) * (at_ms - s.start_ms) / max(1, s.end_ms - s.start_ms))
            heard.append(" ".join(words[:n]))
    return BargeIn(during=during, at_ms=at_ms, heard_text=" ".join(h for h in heard if h))


@dataclass
class TrackEvent:
    speaker: str
    """`child` or `learner`."""
    start_ms: int
    end_ms: int
    text: str


@dataclass
class Exchange:
    transcript: Transcript
    timing: TurnTiming
    result: TurnResult
    child: RenderedSpeech
    waited: TurnResult | None = None
    """The child went on during the learner's long silence (wait turn, plan lot 5), before the learner spoke."""


@dataclass
class VoiceConversation:
    session: Session
    speaker: Speaker
    listener: Listener
    track: Audio | None = None
    events: list[TrackEvent] = field(default_factory=list)
    _last: RenderedSpeech | None = None
    _last_start: int = 0
    """Track offset where the child's last reply audio starts."""

    def exchange(self, learner: Audio, after_ms: int = 800, *, tag: str | None = None) -> Exchange:
        """One learner turn. `tag`: manual classification tag (e.g. "inv", "dir:d_karim"), prefixed
        to the transcript for the manual classifier."""
        prompt = self.session.history[-1][1] if self.session.history else None  # the child's last words
        transcript = self.listener.transcribe(learner, prompt=prompt)
        if not transcript.text.strip():
            raise ValueError("aucune parole entendue dans l'enregistrement")
        # Timing from the audio energy (STT word timings are off by a few hundred ms).
        bounds = learner.voiced_bounds()
        speech_start, speech_end = bounds if bounds else (transcript.speech_start_ms or 0,
                                                          transcript.speech_end_ms or learner.duration_ms)
        child_end = self._last_start + (self._last.audio.duration_ms if self._last else 0)
        waited = None
        threshold = self.session.params["wait_turn_ms"]
        if self._last is not None and after_ms + speech_start >= threshold:
            # A long silence after the reply: the child may go on before the learner speaks.
            waited = self.session.wait(timing=TurnTiming(wait_ms=threshold))
            if waited.decision.speech_act != SpeechAct.SILENCE:
                more = render_speech(waited.speech_plan, self.speaker, waited.decision.delivery)
                at = child_end + threshold
                self.track.mix_at(more.audio, at)
                self.events.append(TrackEvent("child", at + more.onset_ms, at + more.audio.duration_ms, waited.response))
                self._last, self._last_start = more, at
                after_ms -= threshold  # the rest of the silence comes after the continuation
                child_end = at + more.audio.duration_ms
        wait = after_ms + speech_start
        barge = None
        if self._last is not None and wait < 0:
            barge = barge_in_at(self._last, self._last.audio.duration_ms + wait)
        timing = TurnTiming(
            wait_ms=wait, barge_in=barge,
            speech_ms=speech_end - speech_start,
        )
        utterance = f"[{tag}] {transcript.text}" if tag else transcript.text
        result = self.session.turn(utterance, timing=timing)
        child = render_speech(result.speech_plan, self.speaker, result.decision.delivery)

        # -- conversation track ---------------------------------------------------
        if self.track is None:
            self.track = Audio(child.audio.sample_rate)
        if barge is not None:  # the child stops shortly after being interrupted
            cut = self._last_start + barge.at_ms + CHILD_REACTION_MS
            self.track.samples = self.track.samples[: self._ms_to_samples(cut)]
            self.events[-1].end_ms = min(self.events[-1].end_ms, cut)
            self.events[-1].text = barge.heard_text + " —"
        learner_at = max(0, child_end + after_ms)
        self.track.mix_at(learner.resampled(self.track.sample_rate), learner_at)
        self.events.append(TrackEvent("learner", learner_at + speech_start, learner_at + speech_end, transcript.text))
        child_at = learner_at + speech_end
        self.track.mix_at(child.audio, child_at)
        self.events.append(TrackEvent("child", child_at + child.onset_ms, child_at + child.audio.duration_ms,
                                      result.response))
        self._last, self._last_start = child, child_at
        return Exchange(transcript, timing, result, child, waited)

    def _ms_to_samples(self, ms: int) -> int:
        return round(self.track.sample_rate * ms / 1000)
