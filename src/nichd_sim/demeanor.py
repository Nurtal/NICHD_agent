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

from nichd_sim.delivery import TREMOR_AUDIBLE, Delivery, HesitationCause, Volume
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


# -- stage direction ------------------------------------------------------------
# Gender-neutral French (the profile has no gender): noun phrases, present participles and
# epicene adjectives only. One phrasing per cue and intensity: (slight, clear, strong).

_PHRASES: dict[Cue, tuple[str, str, str]] = {
    Cue.GAZE_STEADY: ("jetant un œil vers vous", "le regard posé sur vous", "vous regardant bien en face"),
    Cue.GAZE_BLANK: ("le regard un peu fixe", "le regard fixe, dans le vide", "le regard vide, perdu au loin"),
    Cue.GAZE_AVERTED: ("le regard qui s'échappe", "le regard fuyant", "évitant votre regard"),
    Cue.GAZE_DOWN: ("les yeux un peu baissés", "les yeux baissés", "le regard rivé au sol"),
    Cue.FIDGET_LEGS: ("un pied qui bouge", "les jambes qui s'agitent", "les jambes qui s'agitent sans arrêt"),
    Cue.FIDGET_HANDS: ("les doigts qui remuent", "les mains qui s'agitent", "les mains qui ne tiennent pas en place"),
    Cue.FIDGET_OBJECT: ("touchant sa manche", "tripotant sa manche", "tirant sans arrêt sur sa manche"),
    Cue.TENSION_SHOULDERS: ("les épaules un peu raides", "les épaules crispées", "les épaules remontées, crispées"),
    Cue.TENSION_FISTS: ("les mains serrées", "les poings serrés", "les poings serrés très fort"),
    Cue.TENSION_JAW: ("la mâchoire un peu serrée", "la mâchoire serrée", "les dents serrées"),
    Cue.BREATHING_FAST: ("la respiration un peu courte", "la respiration rapide", "la respiration rapide et saccadée"),
    Cue.BREATHING_HELD: ("retenant un peu son souffle", "retenant son souffle", "le souffle bloqué"),
    Cue.TREMOR_HANDS: ("les mains qui tremblent un peu", "les mains qui tremblent", "les mains tremblantes"),
    Cue.TREMOR_CHIN: ("le menton qui tremble un peu", "le menton qui tremble", "le menton tremblant"),
    Cue.WITHDRAWAL_CURLED: ("le dos voûté", "les genoux ramenés contre soi", "les genoux serrés contre la poitrine"),
    Cue.WITHDRAWAL_ARMS: ("les bras croisés", "les bras serrés contre soi", "les bras serrés autour du corps"),
    Cue.FREEZE_STILL: ("presque immobile", "immobile", "immobile, sans un geste"),
    Cue.FREEZE_ABSENT: ("l'air ailleurs", "le visage sans expression", "le visage vide, comme ailleurs"),
    Cue.TEARS_WET_EYES: ("les yeux qui brillent", "les yeux humides", "les yeux pleins de larmes"),
    Cue.TEARS_CRYING: ("une larme qui coule", "en larmes", "en pleurs, le visage dans les mains"),
    Cue.EASE_RELAXED: ("l'air tranquille", "l'air détendu", "très à l'aise"),
    Cue.EASE_SMILE: ("un petit sourire", "en souriant", "avec un grand sourire"),
}


def _voice(delivery: Delivery, text: str | None) -> list[str]:
    """What the learner hears, in words (no causes). `text`: the reply, when known — a one-word
    reply has no false start (see `plan_speech`)."""
    out = []
    if delivery.onset_ms >= 2500:
        out.append("après un long silence")
    elif delivery.onset_ms >= 1500:
        out.append("après un silence")
    shaking = delivery.tremor >= TREMOR_AUDIBLE
    if delivery.volume == Volume.WHISPER:
        out.append("en chuchotant")
    if delivery.volume == Volume.LOW:
        out.append("d'une voix basse et tremblante" if shaking else "à voix basse")
    elif shaking:
        out.append("d'une voix tremblante")
    if delivery.rate > 1.1:
        out.append("très vite")
    elif delivery.rate < 0.85:
        out.append("lentement")
    stammers = delivery.false_starts and (text is None or len(text.split()) >= 2)
    if stammers:
        out.append("en bafouillant")
    elif delivery.fillers or len(delivery.pauses_ms) >= 2:
        out.append("en hésitant")
    return out


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " et " + parts[-1]


def stage_direction(
    demeanor: Demeanor | None, delivery: Delivery | None = None, *, silent: bool = False, text: str | None = None
) -> str:
    """The stage direction the learner reads before the child's words, e.g.
    « Les yeux baissés, les jambes qui s'agitent — après un long silence, à voix basse ».

    A rendering of the engine's decision, never generated (ADR 0003). Empty for logs older than
    format 3."""
    if demeanor is None:
        return ""
    body = [_PHRASES[c.cue][INTENSITY_ORDER[c.intensity]] for c in demeanor.cues]
    voice = [] if delivery is None or silent else _voice(delivery, text)
    if silent:
        voice = ["sans un mot"]
    text = _join(body) if body else ""
    if voice:
        text = f"{text} — {', '.join(voice)}" if text else ", ".join(voice)
    return text[:1].upper() + text[1:]
