"""Performance contract (ADR 0004): what the child does at each turn, for any body that plays it.

The engine decides; a body (the three.js avatar today, VR tomorrow) only plays. This module turns a
logged turn into a self-contained, versioned description: the words, a timeline of speech and
silences (from the rendered audio when there is one, else estimated), the voice, and the body cues.
No causes and no engine internals: a body shows the child, it does not explain it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from nichd_sim.delivery import ChunkKind, plan_speech
from nichd_sim.demeanor import CUE_LABELS, INTENSITY_LABELS, stage_direction
from nichd_sim.engine import SpeechAct
from nichd_sim.feedback import WAIT_LABEL

if TYPE_CHECKING:
    from nichd_sim.session import SessionLog, TurnRecord
    from nichd_sim.voice import RenderedSpeech, Speaker

PERFORMANCE_FORMAT = 1
ESTIMATED_MS_PER_CHAR = 65.0
"""Speaking time per character when no audio was rendered (child speech, ~12 characters per second)."""


class Span(BaseModel):
    kind: ChunkKind
    start_ms: int
    end_ms: int
    text: str = ""


class Voice(BaseModel):
    volume: str = "normal"
    rate: float = 1.0
    tremor: float = 0.0
    false_starts: int = 0


class BodyCue(BaseModel):
    cue: str
    family: str
    intensity: str
    """`slight`, `clear` or `strong`."""
    label: str = ""
    """French label, for the body's legend."""


class Body(BaseModel):
    arousal: float | None = None
    """None for logs older than format 3 (no demeanor)."""
    style: str | None = None
    cues: list[BodyCue] = []


class TurnPerformance(BaseModel):
    turn: int
    interviewer: str
    response: str
    speech_act: str
    stage_direction: str = ""
    timeline: list[Span]
    duration_ms: int
    timing: str
    """`audio` (measured on the rendered audio) or `estimated`."""
    audio: str | None = None
    """File name of the reply's audio, next to performance.json."""
    voice: Voice
    body: Body


class Child(BaseModel):
    name: str
    age: int


class SessionPerformance(BaseModel):
    format: int = PERFORMANCE_FORMAT
    session_id: str
    scenario_id: str
    child: Child
    turns: list[TurnPerformance]


def estimate_timeline(text: str, delivery) -> list[Span]:
    """Timeline without audio: silences exact, speech from the text length and the rate."""
    rate = delivery.rate if delivery is not None else 1.0
    spans, t = [], 0
    for chunk in plan_speech(text, delivery):
        if chunk.kind == ChunkKind.SILENCE:
            ms = chunk.ms
        else:
            ms = round(len(chunk.text.strip()) * ESTIMATED_MS_PER_CHAR / max(rate, 0.1))
        spans.append(Span(kind=chunk.kind, start_ms=t, end_ms=t + ms, text=chunk.text))
        t += ms
    return spans


def build_turn(turn: TurnRecord, rendered: RenderedSpeech | None = None, audio: str | None = None) -> TurnPerformance:
    d = turn.decision
    text = turn.heard_response if turn.heard_response is not None else turn.response
    if rendered is not None:
        timeline = [Span(kind=s.kind, start_ms=s.start_ms, end_ms=s.end_ms, text=s.text) for s in rendered.timeline]
        timing = "audio"
    else:
        timeline = estimate_timeline(text, d.delivery)
        timing = "estimated"
    voice = Voice()
    if d.delivery is not None:
        voice = Voice(volume=str(d.delivery.volume), rate=d.delivery.rate, tremor=d.delivery.tremor,
                      false_starts=d.delivery.false_starts)
    body = Body()
    if d.demeanor is not None:
        body = Body(
            arousal=d.demeanor.arousal, style=str(d.demeanor.style),
            cues=[BodyCue(cue=str(c.cue), family=str(c.cue.family), intensity=str(c.intensity),
                          label=f"{CUE_LABELS[c.cue]} ({INTENSITY_LABELS[c.intensity]})") for c in d.demeanor.cues],
        )
    return TurnPerformance(
        turn=turn.index,
        interviewer=WAIT_LABEL if turn.kind == "wait" else (turn.classification.clean_text or turn.utterance),
        response=text,
        speech_act=str(d.speech_act),
        stage_direction=stage_direction(d.demeanor, d.delivery, silent=d.speech_act == SpeechAct.SILENCE, text=text),
        timeline=timeline,
        duration_ms=timeline[-1].end_ms if timeline else 0,
        timing=timing,
        audio=audio,
        voice=voice,
        body=body,
    )


def build_session(log: SessionLog, child_name: str, child_age: int, scenario_id: str | None = None,
                  speaker: Speaker | None = None, out_dir: str | Path | None = None) -> SessionPerformance:
    """The whole session. With a `speaker` and an `out_dir`, each reply is rendered to
    `turn_NNN.wav` and the timeline is measured on the audio."""
    turns = []
    for t in log.turns:
        rendered, audio = None, None
        if speaker is not None and out_dir is not None:
            from nichd_sim.voice import render_speech

            text = t.heard_response if t.heard_response is not None else t.response
            rendered = render_speech(plan_speech(text, t.decision.delivery), speaker, t.decision.delivery)
            audio = f"turn_{t.index:03d}.wav"
            rendered.audio.write_wav(Path(out_dir) / audio)
        turns.append(build_turn(t, rendered, audio))
    return SessionPerformance(
        session_id=log.session_id, scenario_id=scenario_id or log.scenario_id,
        child=Child(name=child_name, age=child_age), turns=turns,
    )


def write_session(perf: SessionPerformance, out_dir: str | Path) -> Path:
    path = Path(out_dir) / "performance.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(perf.model_dump_json(indent=2), encoding="utf-8")
    return path


def json_schema() -> dict:
    """The contract's JSON schema (for bodies written in other languages)."""
    return SessionPerformance.model_json_schema()
