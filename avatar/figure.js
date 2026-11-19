// The stage and a stylized seated child, facing the interviewer (+z). Every part the cues act on is
// exposed: pivots to rotate, one material per body part to highlight. No behaviour here: see cues.js.
import * as THREE from "three";
import { inOwner, outerCorner, skinnedMesh, tubeGeometry } from "./body.js";

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
  dev: { position: [1.14, 0.98, 1.84], target: [0.02, 0.63, 0.1] }, // three-quarter view: the gaze axis reads clearly
};

export const BROW_Y = 0.147;
export const LIP_Y = 0.0475;

/** One point of a soft bump on the unit sphere. */
function bump(p, cx, cy, cz, sigma) {
  const d = (p.x - cx) ** 2 + (p.y - cy) ** 2 + (p.z - cz) ** 2;
  return Math.exp(-d / (2 * sigma * sigma));
}

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

// Width of the head by height: straight temples, then a marked jaw angle and a narrow chin.
const JAW = [[-1, 0.46], [-0.86, 0.66], [-0.64, 0.88], [-0.36, 0.98], [0.2, 1], [1, 1]];
function jawWidth(y) {
  for (let i = 1; i < JAW.length; i++) {
    const [y0, w0] = JAW[i - 1], [y1, w1] = JAW[i];
    if (y <= y1) return w0 + ((w1 - w0) * (y - y0)) / (y1 - y0);
  }
  return 1;
}

/** A child's face rather than a ball: brow, eye sockets, cheekbones, nose bridge, jaw angle, chin. */
function faceGeometry(radius) {
  const geo = new THREE.SphereGeometry(1, 72, 54);
  geo.rotateY(-Math.PI / 2); // the seam goes to the back of the head, under the hair
  const pos = geo.attributes.position, p = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    p.fromBufferAttribute(pos, i);
    const front = smooth(-0.1, 0.65, p.z), low = smooth(0.05, -0.85, p.y);
    let out = 1;
    for (const s of [-1, 1]) {
      out += 0.075 * bump(p, 0.6 * s, -0.25, 0.75, 0.2); // cheekbones and round cheeks
      out -= 0.05 * bump(p, 0.37 * s, 0.1, 0.92, 0.13); // eye sockets
      out += 0.022 * bump(p, 0.36 * s, 0.34, 0.86, 0.13); // brow ridge
      out -= 0.022 * bump(p, 0.3 * s, -0.62, 0.72, 0.12); // hollow under the cheek
    }
    out += 0.03 * Math.exp(-(p.x * p.x) / 0.007) * smooth(0.28, 0.05, p.y) * smooth(-0.3, -0.05, p.y) * front; // nose bridge
    out += 0.03 * bump(p, 0, -0.84, 0.54, 0.13); // chin
    out -= 0.018 * bump(p, 0, -0.62, 0.78, 0.07); // dip under the lower lip
    const w = jawWidth(p.y);
    pos.setXYZ(i,
      radius * out * p.x * w,
      radius * out * (p.y * 1.03 - 0.07 * front * smooth(-0.42, -0.95, p.y)),
      radius * out * p.z * (p.z > 0 ? 0.97 : 1) * (1 - 0.13 * low * front));
  }
  geo.computeVertexNormals();
  return geo;
}

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
    new THREE.MeshStandardMaterial({ color: "#dfe4eb" }));
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

  /** user: the room fills the window. dev: a neutral stage in its own panel. */
  function setView(mode, controls) {
    const view = VIEWS[mode];
    camera.position.set(...view.position);
    controls.target.set(...view.target);
    controls.update();
    const user = mode === "user";
    floor.visible = !user;
    scene.background = user ? null : background;
    hemi.intensity = user ? 1.05 : 1.6;
    hemi.groundColor.set(user ? "#dcc8b2" : "#b9c2cf"); // the room's warm floor, not a grey bounce on the face
    sun.intensity = user ? 0.95 : 1.6;
    sun.color.set(user ? "#fff3e4" : "#ffffff");
    offset = user ? 0.12 : 0;
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
    pupil: mat(BASE.pupil, 0.25), hair: mat(BASE.hair, 0.72),
    iris: mat(new THREE.Color("#6b4a2f"), 0.3), glint: new THREE.MeshBasicMaterial({ color: "#ffffff" }),
    shade: mat(new THREE.Color("#c9a08c"), 0.8), freckle: mat(new THREE.Color("#c49478"), 0.8),
    lip: mat(new THREE.Color("#d58d84"), 0.5), stripe: mat(new THREE.Color("#e8dfcf"), 0.95),
    cuff: mat(new THREE.Color("#5b8890"), 0.95), sole: mat(new THREE.Color("#8c8780"), 0.8),
    seat: mat(BASE.trousers, 0.9), lace: mat(new THREE.Color("#f7f4ee"), 0.8),
    blush: new THREE.MeshStandardMaterial({ color: "#ec8f86", transparent: true, opacity: 0.3, roughness: 0.9, depthWrite: false }),
    halo: new THREE.MeshBasicMaterial({ color: "#2a78d6", transparent: true, opacity: 0.55 }),
    tear: new THREE.MeshStandardMaterial({ color: "#8cc8ff", transparent: true, opacity: 0.85, roughness: 0.1 }),
  };
  parts.eyes = [m.eyeL, m.eyeR];
  for (const eye of parts.eyes) { eye.emissive.set("#ffffff"); eye.emissiveIntensity = 0.2; } // whites stay clean in shade
  parts.chest.push(m.stripe);

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

  // skeleton: the pivots the cues turn are bones, so the sleeves, trousers and neck bend at the joints
  const root = new THREE.Bone(); // pelvis, on the seat
  root.position.set(0, 0.47, -0.04);
  scene.add(root);
  const torso = new THREE.Bone(); // pivot at the pelvis: lean, curl
  root.add(torso);
  const neck = new THREE.Bone();
  neck.position.y = 0.4;
  torso.add(neck);
  const head = new THREE.Bone(); // pivot at the neck: gaze yaw/pitch, tremor
  head.scale.setScalar(1.14); // a child's head is large for the body
  neck.add(head);

  // sweater: oval sections, sloping shoulders rising to the neck, ribbed hem, two knitted stripes
  const chest = new THREE.Mesh(new THREE.BufferGeometry(), [m.chest, m.stripe, m.cuff]);
  chest.position.y = 0.175; // breathing scales the sweater from here
  torso.add(chest);
  const ring = (y, rx, rz) => ({ at: torso, p: [0, y, 0], r: [rx, rz] });
  chest.geometry = tubeGeometry(chest, [
    ring(-0.045, 0.104, 0.084), ring(0.02, 0.108, 0.088), ring(0.1, 0.112, 0.09), ring(0.19, 0.12, 0.094),
    ring(0.26, 0.132, 0.091), ring(0.3, 0.142, 0.086), ring(0.328, 0.124, 0.075), ring(0.35, 0.085, 0.062),
    ring(0.366, 0.056, 0.05),
  ], {
    rings: 72, sides: 40, skinned: false,
    groupAt: (t, c) => {
      const y = c.y + chest.position.y;
      return (y > 0.161 && y < 0.179) || (y > 0.206 && y < 0.224) ? 1 : y < 0.022 ? 2 : 0;
    },
  });
  chest.castShadow = true;
  const collar = new THREE.Mesh(new THREE.TorusGeometry(0.047, 0.014, 10, 32), m.cuff);
  collar.rotation.x = Math.PI / 2;
  collar.position.y = 0.36;
  torso.add(collar);
  // trousers' seat: joins the thighs to the sweater
  const trouserSeat = ball(1, m.seat, [0.13, 0.062, 0.118]);
  trouserSeat.position.set(0, 0.004, 0.005);
  root.add(trouserSeat);

  // neck: from the sweater into the head, twisting with it
  skinnedMesh(torso, tubeGeometry(torso, [
    { at: torso, p: [0, 0.335, -0.004], r: [0.046, 0.043], w: { 0: 1 } },
    { at: torso, p: [0, 0.372, -0.003], r: [0.04, 0.038], w: { 0: 0.8, 1: 0.2 } },
    { at: head, p: [0, 0.01, -0.004], r: [0.036, 0.034], w: { 0: 0.3, 1: 0.7 } },
    { at: head, p: [0, 0.045, -0.002], r: [0.036, 0.034], w: { 1: 1 } },
  ], { rings: 16, sides: 24 }), m.neck, [torso, head]);

  const skull = new THREE.Mesh(faceGeometry(0.118), m.head);
  skull.position.y = 0.105;
  skull.castShadow = true;
  head.add(skull);

  // ears, with a darker hollow
  for (const side of [-1, 1]) {
    const ear = ball(0.021, m.head, [0.42, 1.05, 0.72]);
    ear.position.set(0.112 * side, 0.098, -0.004);
    ear.rotation.y = side * 0.35;
    head.add(ear);
    const hollow = ball(0.011, m.shade, [0.3, 1.05, 0.7]);
    hollow.castShadow = false;
    hollow.position.set(0.1185 * side, 0.098, 0);
    hollow.rotation.y = side * 0.35;
    head.add(hollow);
  }

  // nose: bridge, tip, wings and nostrils
  const bridge = capsule(0.0048, 0.02, m.head);
  bridge.position.set(0, 0.106, 0.1125);
  bridge.rotation.x = -0.32;
  head.add(bridge);
  const tip = ball(0.0088, m.head, [1.05, 0.85, 1]);
  tip.position.set(0, 0.0905, 0.1195);
  head.add(tip);
  for (const side of [-1, 1]) {
    const wing = ball(0.0043, m.head);
    wing.position.set(0.0082 * side, 0.0868, 0.1148);
    head.add(wing);
    const nostril = ball(0.0016, m.shade);
    nostril.castShadow = false;
    nostril.position.set(0.0042 * side, 0.0842, 0.1205);
    head.add(nostril);
  }

  // cheeks: a blush that follows the surface (the animator warms it with arousal)
  const cheeks = [];
  for (const side of [-1, 1]) {
    const normal = new THREE.Vector3(0.6 * side, -0.24, 0.76).normalize();
    const cheek = new THREE.Mesh(new THREE.SphereGeometry(0.027, 20, 14), m.blush);
    cheek.position.set(0, 0.105, 0).addScaledVector(normal, 0.1215);
    cheek.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    cheek.scale.set(1, 0.74, 0.1);
    head.add(cheek);
    cheeks.push(cheek);
  }
  // a few freckles across the nose and cheeks
  for (const [x, y] of [[-0.05, 0.097], [-0.036, 0.09], [-0.024, 0.098], [0.024, 0.098], [0.036, 0.09], [0.05, 0.097]]) {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.0014, 6, 5), m.freckle);
    dot.position.set(x, y, Math.sqrt(Math.max(0, 0.0139 - x * x - (y - 0.105) ** 2)) + 0.0015);
    head.add(dot);
  }

  // hair: a cap tilted back to free the face, a fuller back, and pointed locks that break the outline
  const cap = new THREE.Mesh(new THREE.SphereGeometry(0.127, 36, 24, 0, Math.PI * 2, 0, Math.PI * 0.56), m.hair);
  cap.position.y = 0.11;
  cap.rotation.x = -0.65;
  cap.castShadow = true;
  head.add(cap);
  const backHair = ball(0.112, m.hair, [1.04, 0.92, 0.72]);
  backHair.position.set(0, 0.075, -0.05);
  head.add(backHair);
  const lock = (x, y, z, length, width, tiltX, tiltZ) => {
    const geo = new THREE.ConeGeometry(width, length, 5);
    geo.scale(1, 1, 0.45);
    geo.rotateX(Math.PI); // point down
    const mesh = new THREE.Mesh(geo, m.hair);
    mesh.position.set(x, y, z);
    mesh.rotation.set(tiltX, 0, tiltZ);
    mesh.castShadow = true;
    head.add(mesh);
  };
  for (let i = -3; i <= 3; i++) { // fringe, swept slightly to one side
    const a = i * 0.25;
    const length = 0.034 + 0.008 * (i % 2 === 0 ? 1 : 0);
    lock(0.108 * Math.sin(a) + 0.004, 0.181 - 0.018 * a * a, 0.094 * Math.cos(a) + 0.008, length, 0.027, -0.3, 0.08 + 0.2 * a);
  }
  for (const side of [-1, 1]) { // in front of the ears, and behind them
    lock(0.113 * side, 0.106, 0.036, 0.052, 0.021, -0.04, -side * 0.1);
    lock(0.118 * side, 0.08, -0.02, 0.07, 0.027, 0.05, -side * 0.1);
    lock(0.098 * side, 0.056, -0.074, 0.066, 0.03, 0.14, -side * 0.08);
  }

  const eyes = [], brows = [], lids = [];
  for (const [side, em] of [[-1, m.eyeL], [1, m.eyeR]]) {
    const eye = new THREE.Group();
    eye.position.set(0.042 * side, 0.116, 0.095);
    const white = new THREE.Mesh(new THREE.SphereGeometry(0.0205, 24, 16), em);
    white.scale.y = 0.86;
    const iris = new THREE.Mesh(new THREE.SphereGeometry(0.0118, 20, 14), m.iris);
    iris.position.z = 0.0112;
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.0062, 14, 10), m.pupil);
    pupil.position.z = 0.0178;
    const glint = new THREE.Mesh(new THREE.SphereGeometry(0.0021, 8, 6), m.glint);
    glint.position.set(0.0036, 0.0044, 0.0226);
    eye.add(white, iris, pupil, glint);
    head.add(eye);
    eyes.push(eye);

    // upper eyelid and its lash line: outside the eye group, so they do not follow the gaze
    const lid = new THREE.Group();
    lid.position.copy(eye.position);
    const shell = new THREE.Mesh(new THREE.SphereGeometry(0.0212, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), m.head);
    const lash = new THREE.Mesh(new THREE.TorusGeometry(0.0212, 0.0012, 6, 28, Math.PI), m.hair);
    lash.rotation.x = Math.PI / 2;
    lash.rotation.z = Math.PI;
    lid.add(shell, lash);
    head.add(lid);
    lids.push(lid);

    const browGeo = new THREE.CapsuleGeometry(0.0038, 0.027, 4, 8);
    browGeo.rotateZ(Math.PI / 2);
    const brow = new THREE.Mesh(browGeo, m.hair);
    const pivot = new THREE.Group();
    pivot.position.set(0.044 * side, BROW_Y, 0.108);
    pivot.add(brow);
    head.add(pivot);
    brows.push(pivot);
  }

  // the shape is in the geometry: the animator drives the mesh's scale
  const mouthGeo = new THREE.SphereGeometry(0.0195, 18, 10);
  mouthGeo.scale(1, 0.17, 0.26);
  const mouth = new THREE.Mesh(mouthGeo, m.mouth);
  mouth.position.set(0, 0.0555, 0.1075);
  head.add(mouth);
  const lipGeo = new THREE.SphereGeometry(0.012, 14, 8);
  lipGeo.scale(1, 0.26, 0.3);
  const lip = new THREE.Mesh(lipGeo, m.lip);
  lip.position.set(0, LIP_Y, 0.1072);
  head.add(lip);
  const smile = new THREE.Mesh(new THREE.TorusGeometry(0.0175, 0.0024, 8, 18, Math.PI), m.mouth);
  smile.rotation.z = Math.PI;
  smile.position.set(0, 0.0605, 0.1085);
  smile.visible = false;
  head.add(smile);

  const tears = [];
  for (const side of [-1, 1]) {
    const t = new THREE.Mesh(new THREE.SphereGeometry(0.0075, 10, 8), m.tear);
    t.scale.y = 1.4;
    t.position.set(0.053 * side, 0.098, 0.107);
    t.visible = false;
    head.add(t);
    tears.push(t);
  }

  function arm(side) {
    const left = side < 0;
    const shoulder = new THREE.Bone();
    shoulder.position.set(0.145 * side, 0.3, 0);
    torso.add(shoulder);
    const elbow = new THREE.Bone();
    elbow.position.y = -0.17;
    shoulder.add(elbow);
    // resting pose, also the sleeve's bind pose: forearm forward onto the lap, hand on the thigh
    shoulder.rotation.set(0.15, 0, side * 0.02);
    elbow.rotation.set(-1.25, 0, -side * 0.42);
    // one sleeve from the shoulder (weighted on the sweater: a round shoulder) to the wrist
    const S = (y, r, w) => ({ at: shoulder, p: [0, y, 0], r, w });
    const E = (y, r, w) => ({ at: elbow, p: [0, y, 0], r, w });
    const pts = [
      S(-0.005, [0.044, 0.043], { 0: 0.6, 1: 0.4 }),
      S(-0.04, [0.043, 0.042], { 0: 0.15, 1: 0.85 }),
      S(-0.1, [0.038, 0.037], { 1: 1 }),
      S(-0.148, [0.035, 0.034], { 1: 0.85, 2: 0.15 }),
      E(0, [0.034, 0.034], { 1: 0.5, 2: 0.5 }),
      E(-0.035, [0.033, 0.032], { 1: 0.1, 2: 0.9 }),
      E(-0.09, [0.031, 0.029], { 2: 1 }),
      E(-0.14, [0.027, 0.025], { 2: 1 }),
    ];
    const tElbow = 4 / (pts.length - 1);
    const out = outerCorner(inOwner(torso, shoulder, [0, -0.148, 0]), inOwner(torso, elbow, [0, 0, 0]),
      inOwner(torso, elbow, [0, -0.035, 0]));
    const crook = out.clone().negate();
    const bumps = [
      { t: tElbow, dir: out, amp: 0.007, width: 0.03, spread: 0.2 }, // elbow point
      ...[-0.05, 0, 0.05].map((dt, k) => ({ t: tElbow + dt, dir: crook, amp: k === 1 ? -0.004 : 0.003, width: 0.014, spread: 0.3 })),
      { t: 0.08, dir: new THREE.Vector3(side, 0.25, 0).normalize(), amp: 0.004, width: 0.06, spread: 0.4 }, // deltoid
    ];
    skinnedMesh(torso, tubeGeometry(torso, pts, { rings: 44, sides: 24, bumps, groupAt: (t) => (t < tElbow ? 0 : 1) }),
      [left ? m.upperL : m.upperR, left ? m.foreL : m.foreR], [torso, shoulder, elbow]);
    const cuff = new THREE.Mesh(new THREE.TorusGeometry(0.031, 0.0085, 8, 22), m.cuff);
    cuff.rotation.x = Math.PI / 2;
    cuff.position.y = -0.138;
    elbow.add(cuff);
    const handMat = left ? m.handL : m.handR;
    const hand = ball(0.032, handMat, [1, 1.12, 0.72]);
    hand.position.y = -0.17;
    elbow.add(hand);
    for (let i = 0; i < 4; i++) { // fingers, thumb on the inner side
      const finger = capsule(0.0068, 0.02 - Math.abs(i - 1.5) * 0.003, handMat);
      finger.position.set(0.0165 * (i - 1.5) * 0.84, -0.037, 0);
      hand.add(finger);
    }
    const thumb = capsule(0.0078, 0.016, handMat);
    thumb.position.set(-side * 0.031, -0.008, 0.008);
    thumb.rotation.z = side * 0.75;
    hand.add(thumb);
    return { shoulder, elbow, hand };
  }

  function leg(side) {
    const left = side < 0;
    const material = left ? m.legL : m.legR;
    const hip = new THREE.Bone();
    hip.position.set(0.072 * side, 0, 0.02);
    root.add(hip);
    const knee = new THREE.Bone();
    knee.position.z = 0.3;
    hip.add(knee);
    // one trouser leg from the seat to the hem: thigh, kneecap, crease behind the knee, calf, folds
    const H = (z, r, w) => ({ at: hip, p: [0, 0, z], r, w });
    const K = (y, r, w) => ({ at: knee, p: [0, y, 0], r, w });
    const pts = [
      H(-0.035, [0.062, 0.056], { 0: 0.5, 1: 0.5 }),
      H(0.04, [0.062, 0.055], { 1: 1 }),
      H(0.15, [0.057, 0.051], { 1: 1 }),
      H(0.24, [0.05, 0.047], { 1: 0.9, 2: 0.1 }),
      K(0, [0.047, 0.047], { 1: 0.5, 2: 0.5 }),
      K(-0.06, [0.044, 0.045], { 1: 0.05, 2: 0.95 }),
      K(-0.13, [0.043, 0.045], { 2: 1 }),
      K(-0.2, [0.039, 0.04], { 2: 1 }),
      K(-0.245, [0.043, 0.043], { 2: 1 }),
      K(-0.262, [0.045, 0.045], { 2: 1 }),
    ];
    const tKnee = 4 / (pts.length - 1);
    const cap = outerCorner(inOwner(root, hip, [0, 0, 0.24]), inOwner(root, knee, [0, 0, 0]), inOwner(root, knee, [0, -0.06, 0]));
    const back = new THREE.Vector3(0, 0, -1), front = new THREE.Vector3(0, 0, 1), up = new THREE.Vector3(0, 1, 0);
    const bumps = [
      { t: tKnee + 0.01, dir: cap, amp: 0.009, width: 0.025, spread: 0.15 }, // kneecap
      { t: tKnee, dir: cap.clone().negate(), amp: -0.005, width: 0.02, spread: 0.2 }, // behind the knee
      { t: 6 / 9, dir: back, amp: 0.007, width: 0.06, spread: 0.35 }, // calf
      { t: 0.26, dir: up, amp: -0.0025, width: 0.012, spread: 0.3 }, // folds across the thigh
      { t: 0.33, dir: up, amp: -0.002, width: 0.01, spread: 0.3 },
      { t: 0.86, dir: front, amp: -0.003, width: 0.012, spread: 0.3 }, // folds above the hem
      { t: 0.92, dir: front, amp: 0.002, width: 0.01, spread: 0.3 },
    ];
    skinnedMesh(root, tubeGeometry(root, pts, { rings: 56, sides: 26, bumps }), material, [root, hip, knee]);
    const foot = ball(0.05, left ? m.footL : m.footR, [0.95, 0.68, 1.65]);
    foot.position.set(0, -0.3, 0.035);
    knee.add(foot);
    const sole = ball(0.05, m.sole, [0.98, 0.16, 1.68]);
    sole.position.set(0, -0.331, 0.035);
    knee.add(sole);
    for (const [k, dz] of [0.012, 0.03, 0.046].entries()) { // laces across the instep
      const lace = capsule(0.0032, 0.032 - 0.006 * k, m.lace);
      lace.castShadow = false;
      lace.rotation.z = Math.PI / 2;
      lace.position.set(0, -0.3 + 0.034 * Math.sqrt(1 - (dz / 0.0825) ** 2) + 0.0015, 0.035 + dz);
      knee.add(lace);
    }
    return { hip, knee };
  }

  return {
    root, torso, chest, neck, head, eyes, brows, lids, cheeks, mouth, lip, smile, tears, halo, chair, materials: m, parts,
    arms: [arm(-1), arm(1)], legs: [leg(-1), leg(1)],
  };
}
