// Dev view: what the body is doing, made explicit. Gaze axis, highlighted body parts, arousal halo.
// Everything here reads the contract's cues and the figure's real pose; nothing changes the motion.
import * as THREE from "three";
import { CUE_PARTS, FAMILY_COLOR, INTENSITY } from "./cues.js";
import { INTERVIEWER } from "./figure.js";

const UP = new THREE.Vector3(0, 1, 0);
const FORWARD = new THREE.Vector3(0, 0, 1);
const BLUE = new THREE.Color("#2a78d6");
const RED = new THREE.Color("#e34948");
export const AXIS_LENGTH = 0.34;
const FACE_CLEARANCE = 0.1; // the axes start in front of the face, which stays readable
const PART_WEIGHT = { head: 0.5 }; // the whole face turning red would hide the expression
const DEG = 180 / Math.PI;

function restore(mt) {
  mt.color.copy(mt.userData.base);
  mt.emissive.copy(mt.userData.glow.color);
  mt.emissiveIntensity = mt.userData.glow.intensity;
}

function makeArrow(color) {
  const material = new THREE.MeshBasicMaterial({ color, depthTest: false, transparent: true });
  const group = new THREE.Group();
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.0035, 0.0035, AXIS_LENGTH - 0.035, 8), material);
  shaft.position.y = (AXIS_LENGTH - 0.035) / 2;
  const tip = new THREE.Mesh(new THREE.ConeGeometry(0.012, 0.035, 14), material);
  tip.position.y = AXIS_LENGTH - 0.0175;
  group.add(shaft, tip);
  group.renderOrder = 10;
  shaft.renderOrder = tip.renderOrder = 10;
  return group;
}

export class DevOverlay {
  constructor(scene, fig) {
    this.fig = fig;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.gaze = makeArrow(FAMILY_COLOR.gaze);
    const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, AXIS_LENGTH, 0)]);
    this.reference = new THREE.Line(geometry,
      new THREE.LineDashedMaterial({ color: "#5b6475", dashSize: 0.018, gapSize: 0.013, depthTest: false, transparent: true }));
    this.reference.computeLineDistances();
    this.reference.renderOrder = 9;
    this.group.add(this.gaze, this.reference);
    this.levels = {}; // part → {color, target, value}
    for (const [name, mats] of Object.entries(fig.parts)) {
      this.levels[name] = { color: new THREE.Color("#000"), target: 0, value: 0 };
      for (const mt of mats) {
        mt.userData.base = mt.color.clone();
        mt.userData.glow = { color: mt.emissive.clone(), intensity: mt.emissiveIntensity };
      }
    }
    this.visible = true;
  }

  setVisible(on) {
    this.visible = on;
    this.group.visible = on;
    this.fig.halo.visible = on;
    if (!on) {
      for (const mats of Object.values(this.fig.parts)) {
        for (const mt of mats) restore(mt);
      }
    }
  }

  setCues(cues) {
    for (const level of Object.values(this.levels)) level.target = 0;
    for (const c of cues || []) {
      const amount = INTENSITY[c.intensity] ?? 0.5;
      for (const name of CUE_PARTS[c.cue] || []) {
        const level = this.levels[name];
        if (level && amount >= level.target) {
          level.target = amount * (PART_WEIGHT[name] ?? 1);
          level.color.set(FAMILY_COLOR[c.family] || "#999");
        }
      }
    }
  }

  /** Returns the gaze's offset from the interviewer, in degrees (for the legend). */
  update(time, dt, arousal) {
    if (!this.visible) return null;
    const f = this.fig;
    f.materials.halo.color.copy(BLUE).lerp(RED, arousal);
    const pulse = 0.75 + 0.25 * Math.sin(2 * Math.PI * 1.4 * time);
    for (const [name, level] of Object.entries(this.levels)) {
      level.value += (level.target - level.value) * Math.min(1, dt * 5);
      const shown = Math.min(1, 0.45 + 0.55 * level.value) * Math.min(1, level.value * 6); // even a slight cue reads
      for (const mt of f.parts[name]) {
        if (shown < 0.01) { restore(mt); continue; }
        mt.color.copy(mt.userData.base).lerp(level.color, 0.75 * shown);
        mt.emissive.copy(level.color);
        mt.emissiveIntensity = 0.5 * shown * pulse;
      }
    }

    const a = f.eyes[0].getWorldPosition(new THREE.Vector3());
    const origin = f.eyes[1].getWorldPosition(new THREE.Vector3()).add(a).multiplyScalar(0.5);
    const q = f.eyes[0].getWorldQuaternion(new THREE.Quaternion());
    const dir = FORWARD.clone().applyQuaternion(q).normalize();
    const toInterviewer = INTERVIEWER.clone().sub(origin).normalize();
    this.gaze.position.copy(origin).addScaledVector(dir, FACE_CLEARANCE);
    this.gaze.quaternion.setFromUnitVectors(UP, dir);
    this.reference.position.copy(origin).addScaledVector(toInterviewer, FACE_CLEARANCE);
    this.reference.quaternion.setFromUnitVectors(UP, toInterviewer);

    const yaw = (v) => Math.atan2(v.x, v.z) * DEG;
    const pitch = (v) => Math.asin(v.y) * DEG;
    return {
      yaw: yaw(dir) - yaw(toInterviewer),
      pitch: pitch(dir) - pitch(toInterviewer),
      offset: dir.angleTo(toInterviewer) * DEG,
    };
  }
}
