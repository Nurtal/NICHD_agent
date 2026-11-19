// Cue → motion. The engine decides the cues (ADR 0003); this file only plays them.
// The motions are the same in both views. Colours and highlights belong to the dev view: see debug.js.
import { BROW_Y, LIP_Y } from "./figure.js";

export const INTENSITY = { slight: 0.35, clear: 0.65, strong: 1.0 };

// One colour per family: the dev highlight and the legend swatch.
export const FAMILY_COLOR = {
  gaze: "#e87ba4",
  fidget: "#eda100",
  tension: "#e34948",
  breathing: "#eb6834",
  tremor: "#6250d6",
  withdrawal: "#4a5568",
  freeze: "#9aa2b1",
  tears: "#2a78d6",
  ease: "#1baf7a",
};

const HANDS = ["handL", "handR"];
const FOREARMS = ["foreL", "foreR"];
const UPPER_ARMS = ["upperL", "upperR"];
const LEGS = ["legL", "legR", "footL", "footR"];
const WHOLE_BODY = ["head", "neck", "chest", ...UPPER_ARMS, ...FOREARMS, ...HANDS, ...LEGS];

// Which body parts each cue sets in motion. A steady gaze moves nothing: the gaze axis shows it.
export const CUE_PARTS = {
  gaze_steady: [],
  gaze_averted: ["head", "eyes"],
  gaze_down: ["head", "eyes"],
  gaze_blank: ["eyes"],
  fidget_legs: LEGS,
  fidget_hands: [...HANDS, ...FOREARMS],
  fidget_object: ["handR", "foreR", "upperR"],
  tension_shoulders: UPPER_ARMS,
  tension_fists: HANDS,
  tension_jaw: ["mouth"],
  breathing_fast: ["chest"],
  breathing_held: ["chest"],
  tremor_hands: HANDS,
  tremor_chin: ["head", "mouth"],
  withdrawal_arms: [...UPPER_ARMS, ...FOREARMS],
  withdrawal_curled: ["chest", ...LEGS],
  freeze_still: WHOLE_BODY,
  freeze_absent: WHOLE_BODY,
  tears_wet_eyes: ["eyes"],
  tears_crying: ["eyes"],
  ease_relaxed: ["chest"],
  ease_smile: ["chest", "mouth"],
};

const PART_GROUPS = [
  ["corps entier", WHOLE_BODY], ["jambes", LEGS], ["bras", [...UPPER_ARMS, ...FOREARMS]],
  ["mains et avant-bras", [...HANDS, ...FOREARMS]], ["main, bras droit", ["handR", "foreR", "upperR"]],
  ["épaules", UPPER_ARMS], ["mains", HANDS], ["tête et yeux", ["head", "eyes"]], ["tête et bouche", ["head", "mouth"]],
  ["buste et jambes", ["chest", ...LEGS]], ["buste et bouche", ["chest", "mouth"]],
  ["yeux", ["eyes"]], ["bouche", ["mouth"]], ["buste", ["chest"]],
];

/** French name of the parts a cue moves, for the dev legend ("" when none). */
export function cuePartsLabel(cue) {
  const parts = CUE_PARTS[cue] || [];
  const same = (a, b) => a.length === b.length && a.every((p) => b.includes(p));
  return PART_GROUPS.find(([, group]) => same(parts, group))?.[0] ?? "";
}

const ZERO = {
  arousal: 0, gazeYaw: 0, gazePitch: 0, gazeAway: 0, blank: 0,
  fidgetLegs: 0, fidgetHands: 0, fidgetObject: 0,
  tensionShoulders: 0, tensionFists: 0, tensionJaw: 0,
  breathFast: 0, breathHeld: 0, tremorHands: 0, tremorChin: 0,
  withdrawArms: 0, curl: 0, freeze: 0, absent: 0, tears: 0, crying: 0, ease: 0, smile: 0,
  low: 0, whisper: 0, voiceTremor: 0,
};

/** Targets for one turn, from the contract's `body` and `voice`. */
export function targetsFor(body, voice) {
  const t = { ...ZERO, arousal: body.arousal ?? 0.2 };
  for (const c of body.cues || []) {
    const a = INTENSITY[c.intensity] ?? 0.5;
    switch (c.cue) {
      case "gaze_steady": break;
      case "gaze_averted": t.gazeYaw = 1.0 * a; t.gazeAway = a; break;
      case "gaze_down": t.gazePitch = 0.7 * a; t.gazeAway = a; break;
      case "gaze_blank": t.gazeYaw = 0.12; t.gazePitch = -0.05; t.blank = a; break;
      case "fidget_legs": t.fidgetLegs = a; break;
      case "fidget_hands": t.fidgetHands = a; break;
      case "fidget_object": t.fidgetObject = a; break;
      case "tension_shoulders": t.tensionShoulders = a; break;
      case "tension_fists": t.tensionFists = a; break;
      case "tension_jaw": t.tensionJaw = a; break;
      case "breathing_fast": t.breathFast = a; break;
      case "breathing_held": t.breathHeld = a; break;
      case "tremor_hands": t.tremorHands = a; break;
      case "tremor_chin": t.tremorChin = a; break;
      case "withdrawal_arms": t.withdrawArms = a; break;
      case "withdrawal_curled": t.curl = a; break;
      case "freeze_still": t.freeze = a; break;
      case "freeze_absent": t.absent = a; t.blank = Math.max(t.blank, 0.6 * a); break;
      case "tears_wet_eyes": t.tears = a; break;
      case "tears_crying": t.tears = 1; t.crying = a; break;
      case "ease_relaxed": t.ease = a; break;
      case "ease_smile": t.ease = a; t.smile = a; break;
    }
  }
  if (voice) {
    t.low = voice.volume === "low" ? 1 : 0;
    t.whisper = voice.volume === "whisper" ? 1 : 0;
    t.voiceTremor = voice.tremor || 0;
  }
  return t;
}

/** Smoothly moves the figure toward the turn's targets and animates it. */
export class Animator {
  constructor(fig) {
    this.fig = fig;
    this.cur = { ...ZERO };
    this.target = { ...ZERO };
    this.mouthOpen = 0;
    this.smileShown = 0; // 0 → mouth, 1 → smile: crossfaded, never switched
  }

  setTargets(t) { this.target = t; }

  update(time, dt, speaking) {
    const c = this.cur, k = 1 - Math.exp(-dt * 3); // the same easing at any frame rate
    for (const key of Object.keys(c)) c[key] += (this.target[key] - c[key]) * k;
    const f = this.fig;
    const live = 1 - 0.9 * c.freeze; // a frozen child barely moves
    const wave = (hz, phase = 0) => Math.sin(2 * Math.PI * hz * time + phase);

    // breathing follows arousal
    const breathHz = (0.25 + 0.5 * c.arousal) * (1 + 1.5 * c.breathFast);
    const breathAmp = (0.025 + 0.03 * c.arousal) * (1 - c.breathHeld) * live;
    const breath = breathAmp * wave(breathHz);
    f.chest.scale.set(1 + breath, 1 + breath * 0.5, 1 + breath);
    f.halo.scale.setScalar(1 + 0.6 * breath);

    // idle life: a slow sway and shift of weight (incommensurate waves, no visible loop), none when frozen
    const drift = (a, b, c3) => (Math.sin(time * a) + 0.6 * Math.sin(time * b + 1.3) + 0.35 * Math.sin(time * c3 + 2.1)) / 1.95;
    const idle = live * (1 - 0.6 * c.absent);

    // posture: curl forward / lean back at ease
    f.torso.rotation.x = 0.38 * c.curl - 0.08 * c.ease + 0.012 * idle * drift(0.31, 0.53, 0.97);
    f.torso.rotation.z = 0.014 * idle * drift(0.23, 0.41, 0.71);
    for (const [i, leg] of f.legs.entries()) {
      leg.hip.rotation.x = -0.45 * c.curl;
      const side = i === 0 ? 0 : Math.PI;
      leg.knee.rotation.x = 0.28 * c.fidgetLegs * live * wave(3, side);
    }

    // gaze: head and eyes; small saccades unless the gaze is blank or the child frozen
    const saccade = (1 - c.blank) * live * 0.06;
    const yaw = c.gazeYaw + saccade * wave(0.37) + 0.12 * c.gazeAway * wave(0.15);
    f.head.rotation.y = 0.75 * yaw + 0.02 * idle * drift(0.19, 0.37, 0.83);
    f.head.rotation.x = 0.75 * c.gazePitch + 0.14 * c.absent + 0.012 * idle * drift(0.27, 0.45, 1.1);
    f.head.rotation.z = 0.04 * c.tremorChin * wave(11) + 0.01 * c.voiceTremor * wave(9) * (speaking ? 1 : 0);
    for (const eye of f.eyes) {
      eye.rotation.y = 0.5 * yaw + saccade * wave(0.9);
      eye.rotation.x = 0.4 * c.gazePitch;
    }
    // eyelids: follow a lowered gaze, close on a blink
    const since = time % (4.3 + 2 * c.blank), BLINK = 0.16; // closes fast, opens a little slower
    const closed = since < BLINK ? Math.sin(Math.PI * Math.pow(since / BLINK, 0.8)) * Math.max(0, 1 - 2 * c.freeze) : 0;
    const open = -0.34 + 0.55 * c.gazePitch + 0.12 * c.low;
    for (const lid of f.lids) lid.rotation.x = open + (1.25 - open) * closed;
    f.materials.blush.opacity = 0.26 + 0.34 * c.arousal + 0.12 * c.tears;

    // eyebrows: raised in the middle when worried, lowered when tense
    const worry = Math.min(1, Math.max(0, c.arousal - 0.3) * 1.2 + 0.7 * c.tears);
    for (const [i, brow] of f.brows.entries()) {
      brow.rotation.z = (i === 0 ? -1 : 1) * 0.32 * worry;
      brow.position.y = BROW_Y + 0.004 * worry - 0.005 * c.tensionJaw;
    }

    // tears: a drop at the eye when wet, running down when crying
    const wet = Math.min(1, Math.max(0, (c.tears - 0.15) / 0.25)); // the drop grows in, never pops
    for (const [i, tear] of f.tears.entries()) {
      const fall = c.crying > 0.1 ? (time * 0.6 + i * 0.5) % 1 : 0;
      const size = wet * Math.min(1, fall < 0.1 ? 0.4 + 6 * fall : (1 - fall) / 0.15); // a running drop fades at the chin
      tear.visible = size > 0.02;
      tear.scale.set(size, 1.4 * size, size);
      tear.position.y = 0.098 - 0.07 * fall;
    }

    // arms: rest, fidget, object, tension, withdrawal, tremor
    for (const [i, arm] of f.arms.entries()) {
      const side = i === 0 ? -1 : 1;
      arm.shoulder.position.y = 0.3 + 0.035 * c.tensionShoulders;
      arm.shoulder.rotation.z = side * (0.02 - 0.5 * c.withdrawArms);
      arm.shoulder.rotation.y = -side * 0.5 * c.withdrawArms;
      arm.elbow.rotation.x = -1.25 - 0.3 * c.withdrawArms;
      arm.elbow.rotation.z = -side * 0.42 + 0.25 * c.fidgetHands * live * wave(2.5, i); // hands rest on the thighs
      if (i === 1) arm.shoulder.rotation.z += -0.35 * c.fidgetObject + 0.08 * c.fidgetObject * live * wave(2);
      arm.hand.position.x = 0.006 * c.tremorHands * live * wave(13, i);
      arm.hand.scale.set(1 - 0.2 * c.tensionFists, 1.12 * (1 - 0.2 * c.tensionFists), 0.85 * (1 - 0.2 * c.tensionFists));
    }

    // mouth: opens on speech, smaller when low or whispering, shakes with a trembling voice
    const target = speaking ? (0.55 + 0.45 * Math.abs(wave(6.5))) * (1 - 0.35 * c.low - 0.55 * c.whisper) : 0;
    this.mouthOpen += (target - this.mouthOpen) * Math.min(1, dt * 18);
    const smileTarget = c.smile > 0.3 && !speaking ? 1 : 0;
    this.smileShown += (smileTarget - this.smileShown) * (1 - Math.exp(-dt * 8));
    const s = this.smileShown, rest = 1 - s;
    f.mouth.scale.set((1 - 0.3 * c.tensionJaw - 0.15 * this.mouthOpen) * Math.max(0.05, rest), (1 + 3.2 * this.mouthOpen) * Math.max(0.05, rest), 1);
    f.mouth.position.x = 0.002 * c.voiceTremor * wave(12) * (speaking ? 1 : 0); // under 15 Hz: no aliasing at 30 frames/s
    f.lip.position.y = LIP_Y - 0.0085 * this.mouthOpen;
    f.lip.scale.setScalar(Math.max(0.05, rest));
    f.smile.scale.set(Math.max(0.05, s), Math.max(0.05, s), 1);
    f.smile.visible = s > 0.03;
    f.mouth.visible = f.lip.visible = rest > 0.03;
  }
}
