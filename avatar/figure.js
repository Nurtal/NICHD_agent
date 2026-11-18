// The stage and a stylized seated child, facing the interviewer (+z). Every part the cues act on is
// exposed: pivots to rotate, one material per body part to highlight. No behaviour here: see cues.js.
import * as THREE from "three";

export const BASE = {
  skin: new THREE.Color("#f0d3bd"),
  sweater: new THREE.Color("#6f9fa6"),
  trousers: new THREE.Color("#4f5f78"),
  shoe: new THREE.Color("#e9e4dc"),
  hair: new THREE.Color("#5a3b2a"),
  eye: new THREE.Color("#ffffff"),
  pupil: new THREE.Color("#2a1f1a"),
  mouth: new THREE.Color("#a8524e"),
};

/** Where the interviewer sits: the child's steady gaze meets this point. */
export const INTERVIEWER = new THREE.Vector3(0, 1.08, 3.3);

const VIEWS = {
  user: { position: [0, 1.12, 3.4], target: [0, 0.74, 0] },
  dev: { position: [1.5, 1.22, 2.3], target: [0, 0.72, 0] }, // three-quarter view: the gaze axis reads clearly
};

function mat(color, roughness = 0.8) {
  return new THREE.MeshStandardMaterial({ color: color.clone(), roughness, metalness: 0 });
}

function capsule(radius, length, material) {
  const m = new THREE.Mesh(new THREE.CapsuleGeometry(radius, length, 8, 20), material);
  m.castShadow = true;
  return m;
}

function ball(radius, material, scale = [1, 1, 1]) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(radius, 28, 20), material);
  m.scale.set(...scale);
  m.castShadow = true;
  return m;
}

export function buildScene(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const background = new THREE.Color("#eef1f5");
  scene.background = background;
  const camera = new THREE.PerspectiveCamera(38, container.clientWidth / container.clientHeight, 0.05, 50);
  const hemi = new THREE.HemisphereLight("#ffffff", "#b9c2cf", 1.6);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight("#ffffff", 1.6);
  sun.position.set(1.5, 3, 2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.radius = 4;
  scene.add(sun);

  const floor = new THREE.Mesh(new THREE.CircleGeometry(4, 64),
    new THREE.MeshStandardMaterial({ color: "#dfe4eb", transparent: true }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  let offset = 0; // share of the width the image is moved by, to leave room for the panels
  function frame() {
    const w = container.clientWidth, h = container.clientHeight;
    camera.aspect = w / h;
    if (offset) camera.setViewOffset(w, h, offset * w, 0, w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
  window.addEventListener("resize", frame);

  /** user: the room fills the view. dev: neutral stage, transparent over the system map. */
  function setView(mode, withMap, controls) {
    const view = VIEWS[mode];
    camera.position.set(...view.position);
    controls.target.set(...view.target);
    controls.update();
    const user = mode === "user";
    floor.visible = !user;
    floor.material.opacity = withMap ? 0.12 : 1;
    scene.background = user || withMap ? null : background;
    hemi.intensity = user ? 1.05 : 1.6;
    sun.intensity = user ? 0.95 : 1.6;
    sun.color.set(user ? "#fff3e4" : "#ffffff");
    offset = user ? 0.12 : withMap ? -0.21 : 0;
    frame();
  }
  return { renderer, scene, camera, setView };
}

export function buildChild(scene) {
  const parts = {}; // body part → its materials, for the dev highlight
  const part = (name, color, roughness) => (parts[name] = [mat(color, roughness)])[0];
  const m = {
    head: part("head", BASE.skin, 0.65),
    neck: part("neck", BASE.skin, 0.65),
    chest: part("chest", BASE.sweater, 0.95),
    upperL: part("upperL", BASE.sweater, 0.95), upperR: part("upperR", BASE.sweater, 0.95),
    foreL: part("foreL", BASE.sweater, 0.95), foreR: part("foreR", BASE.sweater, 0.95),
    handL: part("handL", BASE.skin, 0.65), handR: part("handR", BASE.skin, 0.65),
    legL: part("legL", BASE.trousers, 0.9), legR: part("legR", BASE.trousers, 0.9),
    footL: part("footL", BASE.shoe, 0.7), footR: part("footR", BASE.shoe, 0.7),
    mouth: part("mouth", BASE.mouth, 0.6),
    eyeL: mat(BASE.eye, 0.3), eyeR: mat(BASE.eye, 0.3),
    pupil: mat(BASE.pupil, 0.25), hair: mat(BASE.hair, 0.9),
    halo: new THREE.MeshBasicMaterial({ color: "#2a78d6", transparent: true, opacity: 0.55 }),
    tear: new THREE.MeshStandardMaterial({ color: "#8cc8ff", transparent: true, opacity: 0.85, roughness: 0.1 }),
  };
  parts.eyes = [m.eyeL, m.eyeR];

  // plain chair of the dev view (the user view seats the child in the room's armchair)
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

  // arousal halo on the floor (dev)
  const halo = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.55, 64), m.halo);
  halo.rotation.x = -Math.PI / 2;
  halo.position.y = 0.005;
  scene.add(halo);

  const root = new THREE.Group(); // pelvis, on the seat
  root.position.set(0, 0.47, -0.04);
  scene.add(root);

  const torso = new THREE.Group(); // pivot at the pelvis: lean, curl
  root.add(torso);
  const chest = capsule(0.115, 0.19, m.chest);
  chest.position.y = 0.175;
  torso.add(chest);
  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.048, 0.016, 10, 28), m.chest);
  collar.rotation.x = Math.PI / 2;
  collar.position.y = 0.355;
  torso.add(collar);
  const neckMesh = capsule(0.04, 0.05, m.neck);
  neckMesh.position.y = 0.38;
  torso.add(neckMesh);

  const neck = new THREE.Group();
  neck.position.y = 0.4;
  torso.add(neck);
  const head = new THREE.Group(); // pivot at the neck: gaze yaw/pitch, tremor
  head.scale.setScalar(1.14); // a child's head is large for the body
  neck.add(head);
  const skull = ball(0.118, m.head, [1, 1.03, 0.98]);
  skull.position.y = 0.105;
  head.add(skull);
  for (const side of [-1, 1]) {
    const ear = ball(0.021, m.head, [0.55, 1, 0.8]);
    ear.position.set(0.116 * side, 0.098, 0);
    head.add(ear);
  }
  const nose = ball(0.012, m.head, [1, 0.9, 1]);
  nose.position.set(0, 0.092, 0.116);
  head.add(nose);

  // hair: a cap tilted back to free the face, a fuller back and a soft fringe
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.127, 36, 24, 0, Math.PI * 2, 0, Math.PI * 0.56), m.hair);
  cap.position.y = 0.108;
  cap.rotation.x = -0.65;
  cap.castShadow = true;
  head.add(cap);
  const backHair = ball(0.112, m.hair, [1.04, 0.92, 0.72]);
  backHair.position.set(0, 0.075, -0.05);
  head.add(backHair);
  const fringe = ball(0.05, m.hair, [1.5, 0.4, 0.62]);
  fringe.position.set(0, 0.178, 0.078);
  fringe.rotation.x = -0.35;
  head.add(fringe);

  const eyes = [], brows = [];
  for (const [side, em] of [[-1, m.eyeL], [1, m.eyeR]]) {
    const eye = new THREE.Group();
    eye.position.set(0.042 * side, 0.118, 0.097);
    const white = new THREE.Mesh(new THREE.SphereGeometry(0.02, 20, 14), em);
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.0125, 16, 12), m.pupil);
    pupil.position.z = 0.0125;
    eye.add(white, pupil);
    head.add(eye);
    eyes.push(eye);
    const brow = new THREE.Mesh(new THREE.CapsuleGeometry(0.0035, 0.026, 4, 8), m.hair);
    brow.rotation.z = Math.PI / 2;
    const pivot = new THREE.Group();
    pivot.position.set(0.043 * side, 0.149, 0.105);
    pivot.add(brow);
    head.add(pivot);
    brows.push(pivot);
  }
  // the shape is in the geometry: the animator drives the mesh's scale
  const mouthGeo = new THREE.SphereGeometry(0.021, 16, 10);
  mouthGeo.scale(1, 0.2, 0.3);
  const mouth = new THREE.Mesh(mouthGeo, m.mouth);
  mouth.position.set(0, 0.059, 0.104);
  head.add(mouth);
  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.0035, 8, 18, Math.PI), m.mouth);
  smile.rotation.z = Math.PI;
  smile.position.set(0, 0.067, 0.103);
  smile.visible = false;
  head.add(smile);

  const tears = [];
  for (const side of [-1, 1]) {
    const t = new THREE.Mesh(new THREE.SphereGeometry(0.008, 10, 8), m.tear);
    t.scale.y = 1.4;
    t.position.set(0.05 * side, 0.098, 0.103);
    t.visible = false;
    head.add(t);
    tears.push(t);
  }

  function arm(side) {
    const left = side < 0;
    const shoulder = new THREE.Group();
    shoulder.position.set(0.145 * side, 0.3, 0);
    torso.add(shoulder);
    const upper = capsule(0.037, 0.13, left ? m.upperL : m.upperR);
    upper.position.y = -0.08;
    shoulder.add(upper);
    const elbow = new THREE.Group();
    elbow.position.y = -0.17;
    shoulder.add(elbow);
    const fore = capsule(0.033, 0.12, left ? m.foreL : m.foreR);
    fore.position.y = -0.075;
    elbow.add(fore);
    const hand = ball(0.036, left ? m.handL : m.handR, [1, 1.12, 0.85]);
    hand.position.y = -0.17;
    elbow.add(hand);
    // resting pose: forearm forward onto the lap
    shoulder.rotation.x = 0.15;
    elbow.rotation.x = -1.25;
    return { shoulder, elbow, hand };
  }

  function leg(side) {
    const left = side < 0;
    const material = left ? m.legL : m.legR;
    const hip = new THREE.Group();
    hip.position.set(0.072 * side, 0, 0.02);
    root.add(hip);
    const thigh = capsule(0.056, 0.22, material);
    thigh.rotation.x = Math.PI / 2;
    thigh.position.z = 0.15;
    hip.add(thigh);
    const knee = new THREE.Group();
    knee.position.z = 0.3;
    hip.add(knee);
    const shin = capsule(0.044, 0.2, material);
    shin.position.y = -0.15;
    knee.add(shin);
    const foot = ball(0.05, left ? m.footL : m.footR, [0.95, 0.68, 1.65]);
    foot.position.set(0, -0.3, 0.035);
    knee.add(foot);
    return { hip, knee };
  }

  return {
    root, torso, chest, neck, head, eyes, brows, mouth, smile, tears, halo, chair, materials: m, parts,
    arms: [arm(-1), arm(1)], legs: [leg(-1), leg(1)],
  };
}
