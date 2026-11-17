// Cue → placeholder marker. The engine decides the cues (ADR 0003); this file only shows them,
// with deliberately simple colours and motions, and a swatch for the legend.
import * as THREE from "three";
import { BASE } from "./figure.js";

export const INTENSITY = { slight: 0.35, clear: 0.65, strong: 1.0 };

// One colour per family: the tint of the body part and the legend swatch.
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

const GREY = new THREE.Color("#a7adb7");
const BLUE = new THREE.Color("#2a78d6");
const RED = new THREE.Color("#e34948");
const tmp = new THREE.Color();

function tint(material, base, color, amount) {
  material.color.copy(base).lerp(tmp.set(color), Math.min(1, Math.max(0, amount)));
}

/** Smoothly moves the figure toward the turn's targets and animates it. */
export class Animator {
  constructor(fig) {
    this.fig = fig;
    this.cur = { ...ZERO };
    this.target = { ...ZERO };
    this.mouthOpen = 0;
  }

  setTargets(t) { this.target = t; }

  update(time, dt, speaking) {
    const c = this.cur, k = Math.min(1, dt * 3);
    for (const key of Object.keys(c)) c[key] += (this.target[key] - c[key]) * k;
    const f = this.fig, m = f.materials;
    const live = 1 - 0.9 * c.freeze; // a frozen child barely moves
    const wave = (hz, phase = 0) => Math.sin(2 * Math.PI * hz * time + phase);

    // arousal: halo colour and breathing
    m.halo.color.copy(BLUE).lerp(RED, c.arousal);
    const breathHz = (0.25 + 0.5 * c.arousal) * (1 + 1.5 * c.breathFast);
    const breathAmp = (0.025 + 0.03 * c.arousal) * (1 - c.breathHeld) * live;
    const breath = breathAmp * wave(breathHz);
    f.torso.children[0].scale.set(1 + breath, 1 + breath * 0.5, 1 + breath);
    f.halo.scale.setScalar(1 + 0.6 * breath);

    // posture: curl forward / lean back at ease
    f.torso.rotation.x = 0.38 * c.curl - 0.08 * c.ease;
    for (const [i, leg] of f.legs.entries()) {
      leg.hip.rotation.x = -0.45 * c.curl;
      const side = i === 0 ? 0 : Math.PI;
      leg.knee.rotation.x = 0.28 * c.fidgetLegs * live * wave(3, side);
    }

    // gaze: head and eyes; small saccades unless the gaze is blank or the child frozen
    const saccade = (1 - c.blank) * live * 0.06;
    const yaw = c.gazeYaw + saccade * wave(0.37) + 0.12 * c.gazeAway * wave(0.15);
    f.head.rotation.y = 0.75 * yaw;
    f.head.rotation.x = 0.75 * c.gazePitch;
    f.head.rotation.z = 0.04 * c.tremorChin * wave(11) + 0.01 * c.voiceTremor * wave(9) * (speaking ? 1 : 0);
    for (const eye of f.eyes) {
      eye.rotation.y = 0.5 * yaw + saccade * wave(0.9);
      eye.rotation.x = 0.4 * c.gazePitch;
    }
    m.pupil.color.copy(BASE.pupil).lerp(GREY, c.blank);
    m.gaze.opacity = 0.85 * Math.max(c.gazeAway, c.blank);
    const eyeColor = c.tears > 0.05 ? FAMILY_COLOR.tears : FAMILY_COLOR.gaze;
    tint(m.eyeL, BASE.eye, eyeColor, Math.max(0.7 * c.tears, 0.25 * c.gazeAway));
    tint(m.eyeR, BASE.eye, eyeColor, Math.max(0.7 * c.tears, 0.25 * c.gazeAway));

    // tears
    for (const [i, tear] of f.tears.entries()) {
      tear.visible = c.crying > 0.1;
      const fall = ((time * 0.6 + i * 0.5) % 1);
      tear.position.y = 0.1 - 0.07 * fall;
    }

    // arms: rest, fidget, object, tension, withdrawal, tremor
    for (const [i, arm] of f.arms.entries()) {
      const side = i === 0 ? -1 : 1;
      arm.shoulder.position.y = 0.36 + 0.035 * c.tensionShoulders;
      arm.shoulder.rotation.z = side * (0.05 - 0.55 * c.withdrawArms);
      arm.shoulder.rotation.y = -side * 0.5 * c.withdrawArms;
      arm.elbow.rotation.x = -1.25 - 0.3 * c.withdrawArms;
      arm.elbow.rotation.z = 0.25 * c.fidgetHands * live * wave(2.5, i);
      if (i === 1) arm.shoulder.rotation.z += -0.35 * c.fidgetObject + 0.08 * c.fidgetObject * live * wave(2);
      const jitter = 0.006 * c.tremorHands * live;
      arm.hand.position.x = jitter * wave(13, i);
      arm.hand.scale.setScalar(1 - 0.2 * c.tensionFists);
    }

    // colours: fidget yellow, tension red, breathing, withdrawal dark, ease green, freeze grey
    const handAmt = Math.max(c.fidgetHands, c.fidgetObject, c.tensionFists, c.tremorHands);
    const handColor = c.tensionFists >= Math.max(c.fidgetHands, c.fidgetObject, c.tremorHands) ? FAMILY_COLOR.tension
      : c.tremorHands >= Math.max(c.fidgetHands, c.fidgetObject) ? FAMILY_COLOR.tremor : FAMILY_COLOR.fidget;
    tint(m.handL, BASE.skin, handColor, 0.8 * handAmt);
    tint(m.handR, BASE.skin, handColor, 0.8 * handAmt);
    tint(m.legL, BASE.trousers, FAMILY_COLOR.fidget, 0.75 * c.fidgetLegs);
    tint(m.legR, BASE.trousers, FAMILY_COLOR.fidget, 0.75 * c.fidgetLegs);
    let shirtColor = FAMILY_COLOR.ease, shirtAmt = 0.5 * c.ease;
    for (const [color, amt] of [[FAMILY_COLOR.tension, 0.6 * c.tensionShoulders],
      [FAMILY_COLOR.breathing, 0.6 * c.breathFast], ["#1baf7a", 0.5 * c.breathHeld],
      [FAMILY_COLOR.withdrawal, 0.6 * Math.max(c.withdrawArms, c.curl)]]) {
      if (amt > shirtAmt) { shirtColor = color; shirtAmt = amt; }
    }
    tint(m.shirt, BASE.shirt, shirtColor, shirtAmt);
    tint(m.skin, BASE.skin, FAMILY_COLOR.freeze, 0.6 * Math.max(c.freeze, c.absent));

    // mouth: opens on speech, smaller when low or whispering, shakes with a trembling voice
    const target = speaking ? (0.55 + 0.45 * Math.abs(wave(6.5))) * (1 - 0.35 * c.low - 0.55 * c.whisper) : 0;
    this.mouthOpen += (target - this.mouthOpen) * Math.min(1, dt * 18);
    f.mouth.scale.set(1 - 0.3 * c.tensionJaw, 1 + 5 * this.mouthOpen, 1);
    f.mouth.position.x = 0.002 * c.voiceTremor * wave(17) * (speaking ? 1 : 0);
    tint(f.materials.mouth, new THREE.Color("#8a3b3b"), FAMILY_COLOR.tension, 0.7 * c.tensionJaw);
    f.smile.visible = c.smile > 0.3 && !speaking;
    f.mouth.visible = !f.smile.visible;
  }
}
