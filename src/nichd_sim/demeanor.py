"""Demeanor: what the child's body shows while it answers (ADR 0003).

The engine decides the demeanor, like the speech act and the delivery: a few cues from a closed
catalogue, each with an intensity. It follows the child's arousal, its effort to remember and its
expression style — never the lie itself, so that no cue gives a lie away (DePaulo et al., 2003).

Demeanor draws come from their own RNG stream ({seed}:demeanor), with a fixed number of draws
per turn, so adding it leaves every other decision unchanged.
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from nichd_sim.delivery import HesitationCause
from nichd_sim.scenario import ExpressionStyle


class CueFamily(StrEnum):
    GAZE = "gaze"
    FIDGET = "fidget"
    TENSION = "tension"
    BREATHING = "breathing"
    TREMOR = "tremor"
    WITHDRAWAL = "withdrawal"
    FREEZE = "freeze"
    TEARS = "tears"
    EASE = "ease"


class Cue(StrEnum):
    GAZE_STEADY = "gaze_steady"
    GAZE_BLANK = "gaze_blank"
    """Fixed, empty stare."""
    GAZE_AVERTED = "gaze_averted"
    GAZE_DOWN = "gaze_down"
    FIDGET_LEGS = "fidget_legs"
    FIDGET_HANDS = "fidget_hands"
    FIDGET_OBJECT = "fidget_object"
    """Plays with a sleeve, its hair."""
    TENSION_SHOULDERS = "tension_shoulders"
    TENSION_FISTS = "tension_fists"
    TENSION_JAW = "tension_jaw"
    BREATHING_FAST = "breathing_fast"
    BREATHING_HELD = "breathing_held"
    TREMOR_HANDS = "tremor_hands"
    TREMOR_CHIN = "tremor_chin"
    WITHDRAWAL_CURLED = "withdrawal_curled"
    WITHDRAWAL_ARMS = "withdrawal_arms"
    FREEZE_STILL = "freeze_still"
    FREEZE_ABSENT = "freeze_absent"
    TEARS_WET_EYES = "tears_wet_eyes"
    TEARS_CRYING = "tears_crying"
    EASE_RELAXED = "ease_relaxed"
    EASE_SMILE = "ease_smile"

    @property
    def family(self) -> CueFamily:
        return CueFamily(self.value.split("_", 1)[0])


class Intensity(StrEnum):
    SLIGHT = "slight"
    CLEAR = "clear"
    STRONG = "strong"


INTENSITY_ORDER = {Intensity.SLIGHT: 0, Intensity.CLEAR: 1, Intensity.STRONG: 2}


class ShownCue(BaseModel):
    model_config = ConfigDict(frozen=True)

    cue: Cue
    intensity: Intensity


class Demeanor(BaseModel):
    model_config = ConfigDict(frozen=True)

    cues: list[ShownCue] = []
    """What the body shows, gaze first, then the strongest cues."""
    arousal: float = 0.0
    """The child's arousal when it answered (trainer mode)."""
    style: ExpressionStyle = ExpressionStyle.MIXED

    def has(self, cue: Cue) -> bool:
        return any(c.cue == cue for c in self.cues)

    def families(self) -> set[CueFamily]:
        return {c.cue.family for c in self.cues}

    def describe(self) -> str:
        """Short summary for trainer mode and the CLI (the learner sees the stage direction)."""
        shown = ", ".join(f"{CUE_LABELS[c.cue]} ({INTENSITY_LABELS[c.intensity]})" for c in self.cues)
        return f"activation {self.arousal:.2f} · {STYLE_LABELS[self.style]} · {shown or 'rien de notable'}"


CUE_LABELS = {
    Cue.GAZE_STEADY: "regard soutenu",
    Cue.GAZE_BLANK: "regard fixe dans le vide",
    Cue.GAZE_AVERTED: "regard fuyant",
    Cue.GAZE_DOWN: "regard baissé",
    Cue.FIDGET_LEGS: "jambes qui s'agitent",
    Cue.FIDGET_HANDS: "mains qui s'agitent",
    Cue.FIDGET_OBJECT: "tripote sa manche ou ses cheveux",
    Cue.TENSION_SHOULDERS: "épaules crispées",
    Cue.TENSION_FISTS: "poings serrés",
    Cue.TENSION_JAW: "mâchoire serrée",
    Cue.BREATHING_FAST: "respiration rapide",
    Cue.BREATHING_HELD: "respiration retenue",
    Cue.TREMOR_HANDS: "mains qui tremblent",
    Cue.TREMOR_CHIN: "menton qui tremble",
    Cue.WITHDRAWAL_CURLED: "recroquevillé",
    Cue.WITHDRAWAL_ARMS: "bras serrés contre soi",
    Cue.FREEZE_STILL: "immobile",
    Cue.FREEZE_ABSENT: "absent",
    Cue.TEARS_WET_EYES: "yeux humides",
    Cue.TEARS_CRYING: "pleure",
    Cue.EASE_RELAXED: "détendu",
    Cue.EASE_SMILE: "sourit",
}
INTENSITY_LABELS = {Intensity.SLIGHT: "léger", Intensity.CLEAR: "net", Intensity.STRONG: "fort"}
STYLE_LABELS = {ExpressionStyle.AGITATED: "agité", ExpressionStyle.FROZEN: "figé", ExpressionStyle.MIXED: "mixte"}


def _intensity(level: float, bounds: list[float]) -> Intensity:
    clear, strong = bounds
    return Intensity.STRONG if level >= strong else Intensity.CLEAR if level >= clear else Intensity.SLIGHT


def _pick(options: list[tuple[Cue, float]], u: float) -> Cue:
    """Weighted choice from one uniform draw (fixed draw count)."""
    total = sum(w for _, w in options)
    acc = 0.0
    for cue, w in options:
        acc += w / total
        if u < acc:
            return cue
    return options[-1][0]


def make_demeanor(
    arousal: float,
    loads: Mapping[HesitationCause, float],
    style: ExpressionStyle,
    params,
    rng: random.Random,
    *,
    sociable: bool = False,
) -> Demeanor:
    """Draw the cues of one turn. `params`: resolved Parameters.

    - `arousal` drives every emotional cue; `loads` add the effort of remembering (gaze turned
      away while thinking) and the confusion. The deception load is deliberately ignored: a lie
      only shows through the arousal it shares with the truth it hides.
    - `sociable`: small talk / acknowledgement, where a calm child may smile.

    Always 2 draws per family + 1 for the gaze, whatever the inputs."""
    p = params
    a = max(0.0, min(1.0, arousal))
    gains = p["expression_gains"][str(style)]
    motor, freeze_gain = gains["motor"], gains["freeze"]
    retrieval = loads.get(HesitationCause.RETRIEVAL, 0.0)
    confusion = loads.get(HesitationCause.CONFUSION, 0.0)
    bounds = p["demeanor_intensity_bounds"]
    tears_from = p["demeanor_tears_arousal"]
    ease_below = p["demeanor_ease_arousal"]

    def above(x: float, lo: float) -> float:
        return max(0.0, (x - lo) / (1.0 - lo)) if x > lo else 0.0

    levels: dict[CueFamily, tuple[float, list[Cue]]] = {
        CueFamily.FIDGET: (
            motor * (p["demeanor_fidget_base"] + 0.8 * a + 0.3 * confusion),
            [Cue.FIDGET_LEGS, Cue.FIDGET_HANDS, Cue.FIDGET_OBJECT],
        ),
        CueFamily.TENSION: (motor * above(a, 0.35), [Cue.TENSION_SHOULDERS, Cue.TENSION_FISTS, Cue.TENSION_JAW]),
        CueFamily.BREATHING: (
            above(a, 0.45),
            [Cue.BREATHING_FAST] if freeze_gain < 0.5 else [Cue.BREATHING_HELD] if motor < 0.5
            else [Cue.BREATHING_FAST, Cue.BREATHING_HELD],
        ),
        CueFamily.TREMOR: (motor * above(a, 0.6), [Cue.TREMOR_HANDS, Cue.TREMOR_CHIN]),
        CueFamily.WITHDRAWAL: (0.7 * above(a, 0.3), [Cue.WITHDRAWAL_ARMS, Cue.WITHDRAWAL_CURLED]),
        CueFamily.FREEZE: (freeze_gain * above(a, 0.4), [Cue.FREEZE_STILL, Cue.FREEZE_ABSENT]),
        CueFamily.TEARS: ((0.6 + 0.4 * motor) * above(a, tears_from), [Cue.TEARS_WET_EYES, Cue.TEARS_CRYING]),
        CueFamily.EASE: (
            max(0.0, (ease_below - a) / ease_below) * (1.0 - 0.5 * confusion),
            [Cue.EASE_SMILE, Cue.EASE_RELAXED] if sociable else [Cue.EASE_RELAXED],
        ),
    }
    shown: list[tuple[float, ShownCue]] = []
    for family, (level, choices) in levels.items():  # fixed iteration order
        level = min(1.0, level)
        u_show, u_pick = rng.random(), rng.random()
        if level <= 0 or u_show >= min(1.0, level * p["demeanor_presence_gain"]):
            continue
        cue = choices[min(len(choices) - 1, int(u_pick * len(choices)))]
        if family == CueFamily.TEARS:  # crying only at the top of the range
            cue = Cue.TEARS_CRYING if level >= bounds[1] else Cue.TEARS_WET_EYES
        if family == CueFamily.FREEZE and freeze_gain < 0.5:
            continue  # an agitated child does not freeze
        shown.append((level, ShownCue(cue=cue, intensity=_intensity(level, bounds))))
    # Gaze: always one. Turned away or down while remembering, with emotion or shyness;
    # blank when frozen; steady when calm. Never from the lie.
    gaze = _pick(
        [
            (Cue.GAZE_STEADY, max(0.05, (1.0 - a) * (1.0 - retrieval))),
            (Cue.GAZE_AVERTED, 0.6 * retrieval + 0.3 * a + 0.2 * confusion),
            (Cue.GAZE_DOWN, 0.7 * a + 0.1),
            (Cue.GAZE_BLANK, freeze_gain * above(a, 0.4)),
        ],
        rng.random(),
    )
    gaze_level = (1.0 - a) if gaze == Cue.GAZE_STEADY else max(a, retrieval)
    # Tears first (the most salient), then by level.
    shown.sort(key=lambda x: (x[1].cue.family != CueFamily.TEARS, -x[0]))
    cues = [ShownCue(cue=gaze, intensity=_intensity(gaze_level, bounds))]
    cues += [sc for _, sc in shown[: p["demeanor_max_cues"]]]
    return Demeanor(cues=cues, arousal=round(a, 3), style=style)
