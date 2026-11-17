// A child made of primitives, seated, facing the interviewer (+z). Every part the cues act on is
// exposed: pivots to rotate, materials to tint. No behaviour here: see cues.js.
import * as THREE from "three";

export const BASE = {
  skin: new THREE.Color("#e9d2bf"),
  shirt: new THREE.Color("#9fb4cc"),
  trousers: new THREE.Color("#5f6f86"),
  eye: new THREE.Color("#ffffff"),
  pupil: new THREE.Color("#1c2230"),
};

function mat(color) {
  return new THREE.MeshStandardMaterial({ color: color.clone(), roughness: 0.75, metalness: 0.0 });
}

function capsule(radius, length, material) {
  const m = new THREE.Mesh(new THREE.CapsuleGeometry(radius, length, 6, 16), material);
  m.castShadow = true;
  return m;
}

export function buildScene(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.shadowMap.enabled = true;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#eef1f5");
  const camera = new THREE.PerspectiveCamera(38, container.clientWidth / container.clientHeight, 0.05, 50);
  camera.position.set(0.55, 1.2, 2.75); // seated interviewer's eyes, slightly to the side
  scene.add(new THREE.HemisphereLight("#ffffff", "#b9c2cf", 1.6));
  const sun = new THREE.DirectionalLight("#ffffff", 1.6);
  sun.position.set(1.5, 3, 2);
  sun.castShadow = true;
  scene.add(sun);

  const floor = new THREE.Mesh(new THREE.CircleGeometry(4, 64), new THREE.MeshStandardMaterial({ color: "#dfe4eb" }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });
  return { renderer, scene, camera };
}

export function buildChild(scene) {
  const m = {
    skin: mat(BASE.skin), shirt: mat(BASE.shirt), trousers: mat(BASE.trousers),
    handL: mat(BASE.skin), handR: mat(BASE.skin), legL: mat(BASE.trousers), legR: mat(BASE.trousers),
    eyeL: mat(BASE.eye), eyeR: mat(BASE.eye), pupil: mat(BASE.pupil), mouth: mat(new THREE.Color("#8a3b3b")),
    halo: new THREE.MeshBasicMaterial({ color: "#2a78d6", transparent: true, opacity: 0.55 }),
    tear: new THREE.MeshStandardMaterial({ color: "#4aa3ff", transparent: true, opacity: 0.85 }),
  };

  // chair
  const chairMat = new THREE.MeshStandardMaterial({ color: "#b98d5a", roughness: 0.8 });
  const chair = new THREE.Group();
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.04, 0.4), chairMat);
  seat.position.y = 0.4;
  const back = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.45, 0.04), chairMat);
  back.position.set(0, 0.64, -0.2);
  chair.add(seat, back);
  for (const [x, z] of [[-0.19, -0.17], [0.19, -0.17], [-0.19, 0.17], [0.19, 0.17]]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.4, 0.03), chairMat);
    leg.position.set(x, 0.2, z);
    chair.add(leg);
  }
  chair.traverse((o) => { o.castShadow = true; });
  scene.add(chair);

  // arousal halo on the floor
  const halo = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.55, 64), m.halo);
  halo.rotation.x = -Math.PI / 2;
  halo.position.y = 0.005;
  scene.add(halo);

  const root = new THREE.Group(); // pelvis, on the seat
  root.position.set(0, 0.47, -0.04);
  scene.add(root);

  const torso = new THREE.Group(); // pivot at the pelvis: lean, curl, breathe
  root.add(torso);
  const chest = capsule(0.13, 0.26, m.shirt);
  chest.position.y = 0.2;
  torso.add(chest);

  const neck = new THREE.Group();
  neck.position.y = 0.44;
  torso.add(neck);
  const head = new THREE.Group(); // pivot at the neck: gaze yaw/pitch, tremor
  neck.add(head);
  const skull = new THREE.Mesh(new THREE.SphereGeometry(0.115, 32, 24), m.skin);
  skull.position.y = 0.1;
  skull.castShadow = true;
  head.add(skull);

  const eyes = [];
  for (const [side, em] of [[-1, m.eyeL], [1, m.eyeR]]) {
    const eye = new THREE.Group();
    eye.position.set(0.04 * side, 0.125, 0.098);
    const white = new THREE.Mesh(new THREE.SphereGeometry(0.022, 16, 12), em);
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.011, 12, 8), m.pupil);
    pupil.position.z = 0.016;
    eye.add(white, pupil);
    head.add(eye);
    eyes.push(eye);
  }
  const mouth = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.008, 0.01), m.mouth);
  mouth.position.set(0, 0.055, 0.108);
  head.add(mouth);
  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.026, 0.004, 6, 16, Math.PI), m.mouth);
  smile.rotation.z = Math.PI;
  smile.position.set(0, 0.064, 0.106);
  smile.visible = false;
  head.add(smile);

  // gaze ray: a placeholder for where the child looks, shown when the gaze leaves the interviewer
  const gazeMat = new THREE.MeshBasicMaterial({ color: "#e87ba4", transparent: true, opacity: 0 });
  const gazeRay = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.7, 6), gazeMat);
  gazeRay.rotation.x = Math.PI / 2;
  gazeRay.position.set(0, 0.125, 0.45);
  head.add(gazeRay);
  m.gaze = gazeMat;

  const tears = [];
  for (const side of [-1, 1]) {
    const t = new THREE.Mesh(new THREE.SphereGeometry(0.013, 10, 8), m.tear);
    t.position.set(0.04 * side, 0.1, 0.11);
    t.visible = false;
    head.add(t);
    tears.push(t);
  }

  function arm(side) {
    const shoulder = new THREE.Group();
    shoulder.position.set(0.17 * side, 0.36, 0);
    torso.add(shoulder);
    const upper = capsule(0.04, 0.16, m.shirt);
    upper.position.y = -0.1;
    shoulder.add(upper);
    const elbow = new THREE.Group();
    elbow.position.y = -0.2;
    shoulder.add(elbow);
    const fore = capsule(0.035, 0.14, m.skin);
    fore.position.y = -0.09;
    elbow.add(fore);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.042, 16, 12), side < 0 ? m.handL : m.handR);
    hand.position.y = -0.2;
    hand.castShadow = true;
    elbow.add(hand);
    // resting pose: forearm forward onto the lap
    shoulder.rotation.x = 0.15;
    elbow.rotation.x = -1.25;
    return { shoulder, elbow, hand };
  }

  function leg(side) {
    const hip = new THREE.Group();
    hip.position.set(0.075 * side, 0, 0.02);
    root.add(hip);
    const thigh = capsule(0.055, 0.22, side < 0 ? m.legL : m.legR);
    thigh.rotation.x = Math.PI / 2;
    thigh.position.z = 0.15;
    hip.add(thigh);
    const knee = new THREE.Group();
    knee.position.z = 0.3;
    hip.add(knee);
    const shin = capsule(0.045, 0.22, side < 0 ? m.legL : m.legR);
    shin.position.y = -0.17;
    knee.add(shin);
    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.05, 0.15), m.trousers);
    foot.position.set(0, -0.33, 0.04);
    knee.add(foot);
    return { hip, knee };
  }

  return {
    root, torso, neck, head, eyes, mouth, smile, tears, halo, materials: m,
    arms: [arm(-1), arm(1)], legs: [leg(-1), leg(1)],
  };
}
