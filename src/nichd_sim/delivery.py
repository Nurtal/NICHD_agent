"""Delivery: *how* the child says its answer (silence before speaking, pauses, fillers, rate, volume).

The engine decides the delivery, like the speech act and the allowed units (ADR 0002). It is the
sum of several hesitation causes, each logged with its load, so that hesitation is never a
lie detector: a child also hesitates when searching memory, when upset, or when confused.

Delivery draws come from their own RNG stream, so adding it leaves every engine decision
unchanged.
"""

from __future__ import annotations

import random
import re
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class HesitationCause(StrEnum):
    RETRIEVAL = "retrieval"
    """Searching memory: peripheral detail, time or frequency, young child."""
    AFFECT = "affect"
    """Emotion: central fact of the target event, reluctance."""
    DECEPTION = "deception"
    """Cognitive load of a lie in progress."""
    CONFUSION = "confusion"
    """The question was hard to understand (compound, many options, off-protocol)."""


CAUSE_LABELS = {
    HesitationCause.RETRIEVAL: "mémoire",
    HesitationCause.AFFECT: "émotion",
    HesitationCause.DECEPTION: "mensonge",
    HesitationCause.CONFUSION: "confusion",
}


class Volume(StrEnum):
    NORMAL = "normal"
    LOW = "low"
    WHISPER = "whisper"


class Delivery(BaseModel):
    model_config = ConfigDict(frozen=True)

    onset_ms: int
    """Silence before the first syllable."""
    pauses_ms: list[int] = []
    """Silent pauses inside the reply, in order."""
    fillers: int = 0
    """Number of « euh » inserted (the first one opens the reply)."""
    rate: float = 1.0
    """Relative speech rate (1.0 = normal, lower = slower, higher = rushed under arousal)."""
    volume: Volume = Volume.NORMAL
    loads: dict[HesitationCause, float] = {}
    """Load (0–1) of each hesitation cause: why the child hesitated."""
    hesitation: float = 0.0
    """Combined hesitation (0–1) the delivery was derived from."""
    false_starts: int = 0
    """Restarted openings (« il… il m'a »): stammering (ADR 0003)."""
    tremor: float = 0.0
    """Shaking voice (0–1), from emotion only (ADR 0003)."""

    @property
    def dominant_cause(self) -> HesitationCause | None:
        active = {c: v for c, v in self.loads.items() if v > 0}
        return max(active, key=active.get) if active else None

    def describe(self) -> str:
        """Short French summary for trainer mode and the CLI."""
        parts = [f"silence {self.onset_ms / 1000:.1f} s".replace(".", ",")]
        if self.pauses_ms:
            parts.append(f"{len(self.pauses_ms)} pause(s)")
        if self.fillers:
            parts.append(f"{self.fillers} « euh »")
        if self.rate < 0.9:
            parts.append("débit lent")
        elif self.rate > 1.1:
            parts.append("débit précipité")
        if self.false_starts:
            parts.append(f"{self.false_starts} faux départ(s)")
        if self.tremor >= TREMOR_AUDIBLE:
            parts.append("voix tremblante")
        if self.volume != Volume.NORMAL:
            parts.append("voix basse" if self.volume == Volume.LOW else "chuchote")
        causes = sorted(((v, c) for c, v in self.loads.items() if v > 0), reverse=True)
        if causes:
            parts.append("causes : " + ", ".join(f"{CAUSE_LABELS[c]} {v:.0%}".replace("%", " %") for v, c in causes))
        return " · ".join(parts)


def combine(loads: Mapping[HesitationCause, float], weights: Mapping[str, float]) -> float:
    """Probabilistic OR of the weighted loads: each cause adds hesitation, never beyond 1."""
    rest = 1.0
    for cause, load in loads.items():
        rest *= 1.0 - max(0.0, min(1.0, weights.get(str(cause), 1.0) * load))
    return 1.0 - rest


def _stochastic_round(x: float, rng: random.Random) -> int:
    base = int(x)
    return base + (1 if rng.random() < x - base else 0)


def make_delivery(loads: Mapping[HesitationCause, float], params, rng: random.Random, *, speaks: bool = True) -> Delivery:
    """Turn hesitation loads into a concrete delivery. `params`: resolved Parameters.

    The number of draws per call depends only on the loads, so the stream stays aligned for a
    given sequence of decisions."""
    loads = {HesitationCause(c): round(max(0.0, min(1.0, v)), 3) for c, v in loads.items() if v > 0}
    h = combine(loads, params["hesitation_weights"])
    noise = rng.gauss(0.0, params["delivery_onset_noise_ms"])
    onset = params["delivery_base_onset_ms"] + h * params["delivery_onset_span_ms"] + noise
    onset = int(max(params["delivery_min_onset_ms"], onset))
    n_pauses = _stochastic_round(h * params["delivery_max_pauses"], rng) if speaks else 0
    lo, hi = params["delivery_pause_ms"]
    pauses = [int(lo + (hi - lo) * h * rng.uniform(0.6, 1.4)) for _ in range(n_pauses)]
    fillers = _stochastic_round(h * params["delivery_max_fillers"], rng) if speaks else 0
    low, whisper = params["affect_volume_thresholds"]
    affect = loads.get(HesitationCause.AFFECT, 0.0)
    volume = Volume.WHISPER if affect >= whisper else Volume.LOW if affect >= low else Volume.NORMAL
    return Delivery(
        onset_ms=onset,
        pauses_ms=pauses,
        fillers=fillers,
        rate=round(1.0 - params["delivery_rate_drop"] * h, 3),
        volume=volume,
        loads=loads,
        hesitation=round(h, 3),
    )


TREMOR_AUDIBLE = 0.3
"""Voice tremor from which it is described (and audible)."""


def express(delivery: Delivery, arousal: float, motor: float, params, rng: random.Random, *, speaks: bool = True) -> Delivery:
    """Add what arousal does to the voice (ADR 0003): rushed rate, false starts, tremor.

    `motor`: how much the child's expression style lets arousal show (low for a frozen child,
    whose voice stays flat). Draws from the caller's demeanor stream, never the delivery
    stream, so that the ADR 0002 draws stay aligned. Fixed number of draws per call."""
    p = params
    thr = p["delivery_fast_arousal"]
    rate = delivery.rate
    if arousal > thr:
        rate *= 1.0 + p["delivery_rate_rise"] * motor * (arousal - thr) / (1.0 - thr)
    loads = dict(delivery.loads)
    stammer = combine(loads, p["false_start_weights"]) * (0.5 + 0.5 * motor)
    draw = _stochastic_round(stammer * p["delivery_max_false_starts"], rng)
    lo = p["tremor_affect_threshold"]
    affect = loads.get(HesitationCause.AFFECT, 0.0)
    tremor = max(0.0, (affect - lo) / (1.0 - lo)) * (0.4 + 0.6 * motor) if affect > lo else 0.0
    return delivery.model_copy(
        update={
            "rate": round(rate, 3),
            "false_starts": draw if speaks else 0,
            "tremor": round(min(1.0, tremor), 3),
        }
    )


# -- speech plan --------------------------------------------------------------


class ChunkKind(StrEnum):
    SPEECH = "speech"
    SILENCE = "silence"


class SpeechChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ChunkKind
    text: str = ""
    ms: int = 0


FILLER = "euh…"
FILLER_GAP_MS = 250
FALSE_START_GAP_MS = 200
"""Short break after a restarted opening (« il… [0,2 s] il m'a »)."""
"""Short gap after a filler, so that it does not run into the next word."""
WORDS_PER_PAUSE = 4
"""At most one internal pause per this many words: « je [1 s] sais pas » does not sound like a child."""

# Pause candidates, by preference: after punctuation, before a clause connector, between words.
_TIERS = (
    re.compile(r"(?<=[,;:.…!?])\s+"),
    # before a connector, but not inside a pair of connectors (« et | puis »)
    re.compile(r"(?<!\bet)(?<!\bpuis)(?<!\bmais)\s+(?=(?:et|puis|mais|parce|après|alors)\b)", re.IGNORECASE),
    re.compile(r"\s+"),
)


def _spread(items: list[int], n: int) -> list[int]:
    """n items evenly spread over `items` (all of them if there are fewer)."""
    if len(items) <= n:
        return items
    step = len(items) / n
    return [items[int(step * i + step / 2)] for i in range(n)]


def _split(text: str, n: int) -> list[str]:
    """Split `text` into at most n + 1 pieces, preferring punctuation, then connectors, then words."""
    starts: list[int] = []
    for tier in _TIERS:
        if len(starts) >= n:
            break
        found = sorted({m.end() for m in tier.finditer(text)} - set(starts))
        starts += _spread(found, n - len(starts))
    pieces, prev = [], 0
    for s in sorted(starts):
        pieces.append(text[prev:s].strip())
        prev = s
    pieces.append(text[prev:].strip())
    return [p for p in pieces if p]


def plan_speech(text: str, delivery: Delivery | None) -> list[SpeechChunk]:
    """Speech plan: the reply cut into speech and silence chunks according to the delivery.

    Deterministic for a given (text, delivery). The first filler opens the reply; the other
    fillers resume speech after a pause."""
    text = text.strip()
    if delivery is None:
        return [SpeechChunk(kind=ChunkKind.SPEECH, text=text)] if text else []
    plan = [SpeechChunk(kind=ChunkKind.SILENCE, ms=delivery.onset_ms)]
    if not text or not any(ch.isalnum() for ch in text):  # silence act ("…")
        return plan
    fillers = delivery.fillers
    false_starts = delivery.false_starts
    if fillers:
        plan += [SpeechChunk(kind=ChunkKind.SPEECH, text=FILLER), SpeechChunk(kind=ChunkKind.SILENCE, ms=FILLER_GAP_MS)]
        fillers -= 1
    n_pauses = min(len(delivery.pauses_ms), len(text.split()) // WORDS_PER_PAUSE)
    pieces = _split(text, n_pauses)
    for i, piece in enumerate(pieces):
        if i > 0:
            plan.append(SpeechChunk(kind=ChunkKind.SILENCE, ms=delivery.pauses_ms[i - 1]))
            if fillers:
                plan += [SpeechChunk(kind=ChunkKind.SPEECH, text=FILLER), SpeechChunk(kind=ChunkKind.SILENCE, ms=FILLER_GAP_MS)]
                fillers -= 1
        if false_starts and len(piece.split()) >= 2:
            plan += _false_start(piece)
            false_starts -= 1
        plan.append(SpeechChunk(kind=ChunkKind.SPEECH, text=piece))
    return plan


def _false_start(piece: str) -> list[SpeechChunk]:
    """The opening word said, broken off, then the piece starts again: « il… [0,2 s] il m'a »."""
    first = re.sub(r"[,;:.…!?]+$", "", piece.split()[0])
    if not any(ch.isalnum() for ch in first):
        return []
    return [SpeechChunk(kind=ChunkKind.SPEECH, text=f"{first}…"), SpeechChunk(kind=ChunkKind.SILENCE, ms=FALSE_START_GAP_MS)]


def render_plan(plan: list[SpeechChunk]) -> str:
    """Text rendering of a speech plan (CLI, transcripts): silences as [1,2 s]."""
    out = []
    for ch in plan:
        if ch.kind == ChunkKind.SILENCE:
            if ch.ms >= 300:
                out.append(f"[{ch.ms / 1000:.1f} s]".replace(".", ","))
        else:
            out.append(ch.text)
    return " ".join(out)
