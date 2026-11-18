// A child-friendly hearing room (« salle Mélanie »), for the user view. All procedural, no asset.
// Kept calm on purpose: the room must not distract the child, so nothing lively sits near the child's
// face, and the toys stay on a shelf at the back. The child sits at the origin, facing +z.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const WALL_Z = -1.7, SIDE_X = 3.0, HEIGHT = 2.6;

function std(color, roughness = 0.85) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0 });
}

function place(parent, mesh, x, y, z, { cast = true, receive = true } = {}) {
  mesh.position.set(x, y, z);
  mesh.castShadow = cast;
  mesh.receiveShadow = receive;
  parent.add(mesh);
  return mesh;
}

const box = (w, h, d, material) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
const soft = (w, h, d, r, material) => new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 4, r), material);
const cylinder = (top, bottom, h, material, n = 32) => new THREE.Mesh(new THREE.CylinderGeometry(top, bottom, h, n), material);
const ball = (r, material) => new THREE.Mesh(new THREE.SphereGeometry(r, 24, 16), material);

function drawing(paint) {
  const canvas = document.createElement("canvas");
  canvas.width = 256; canvas.height = 320;
  const g = canvas.getContext("2d");
  g.fillStyle = "#fffdf7";
  g.fillRect(0, 0, 256, 320);
  g.lineWidth = 8; g.lineCap = "round"; g.lineJoin = "round";
  paint(g);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function houseDrawing(g) {
  g.fillStyle = "#f6c945"; g.beginPath(); g.arc(205, 58, 30, 0, 7); g.fill();
  g.fillStyle = "#8fc98a"; g.fillRect(0, 262, 256, 58);
  g.fillStyle = "#f2a48f"; g.fillRect(62, 160, 132, 102);
  g.fillStyle = "#c9604f"; g.beginPath(); g.moveTo(44, 162); g.lineTo(128, 88); g.lineTo(212, 162); g.fill();
  g.fillStyle = "#6c8fc4"; g.fillRect(112, 206, 34, 56);
}

function rainbowDrawing(g) {
  ["#e8746a", "#f3b35a", "#f4dc6b", "#8fc98a", "#7fa9dc"].forEach((color, i) => {
    g.strokeStyle = color; g.lineWidth = 15;
    g.beginPath(); g.arc(128, 228, 104 - i * 16, Math.PI, 0); g.stroke();
  });
  g.fillStyle = "#dfeaf2";
  for (const x of [38, 218]) { g.beginPath(); g.arc(x, 232, 30, 0, 7); g.fill(); }
}

function frame(room, x, y, w, h, texture) {
  place(room, box(w + 0.05, h + 0.05, 0.025, std("#c9a97f", 0.7)), x, y, WALL_Z + 0.015, { receive: false });
  place(room, new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: texture, roughness: 0.9 })),
    x, y, WALL_Z + 0.03, { cast: false, receive: false });
}

function window_(room) {
  const x = -1.08, y = 1.5, w = 0.92, h = 0.98;
  const white = std("#f8f6f1", 0.6);
  place(room, new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: "#d9ebf5" })),
    x, y, WALL_Z + 0.012, { cast: false, receive: false });
  for (const [dx, dy, bw, bh] of [[0, h / 2, w + 0.08, 0.05], [0, -h / 2, w + 0.14, 0.06], [-w / 2, 0, 0.05, h], [w / 2, 0, 0.05, h], [0, 0, 0.025, h]]) {
    place(room, box(bw, bh, 0.05, white), x + dx, y + dy, WALL_Z + 0.03, { receive: false });
  }
  // roller blind, half down: soft light, no view to distract
  place(room, box(w, h * 0.52, 0.012, std("#f4e8d3", 1)), x, y + h * 0.24, WALL_Z + 0.04, { cast: false, receive: false });
  place(room, cylinder(0.02, 0.02, w + 0.04, white, 12), x, y + h / 2 - 0.005, WALL_Z + 0.06, { receive: false }).rotation.z = Math.PI / 2;
}

function plush(room, x, y, z, color) {
  const fur = std(color, 1);
  const bear = new THREE.Group();
  place(bear, ball(0.062, fur), 0, 0.06, 0);
  place(bear, ball(0.048, fur), 0, 0.15, 0.005);
  for (const s of [-1, 1]) {
    place(bear, ball(0.018, fur), 0.036 * s, 0.192, 0);
    place(bear, ball(0.022, fur), 0.06 * s, 0.075, 0.018);
    place(bear, ball(0.025, fur), 0.042 * s, 0.018, 0.045);
  }
  place(bear, ball(0.018, std("#f5e9da", 1)), 0, 0.14, 0.046);
  bear.position.set(x, y, z);
  room.add(bear);
}

function shelf(room) {
  const x = 1.22, depth = 0.3, width = 1.05, z = WALL_Z + depth / 2 + 0.01;
  const wood = std("#e6d3b8", 0.75);
  for (const y of [0.04, 0.42, 0.8]) place(room, box(width, 0.03, depth, wood), x, y, z);
  for (const dx of [-width / 2, width / 2]) place(room, box(0.03, 0.81, depth, wood), x + dx, 0.415, z);
  place(room, box(width, 0.81, 0.012, std("#efe2cf", 0.9)), x, 0.415, WALL_Z + 0.016, { cast: false });
  const colors = ["#7fa2b8", "#d9a07f", "#a9bf97", "#e2c279", "#b39bb8", "#8fb3a9", "#d48f86"];
  let bx = x - width / 2 + 0.05;
  for (let i = 0; i < 12; i++) {
    const w = 0.03 + (i % 3) * 0.008, h = 0.2 + ((i * 7) % 5) * 0.016;
    place(room, box(w, h, 0.17, std(colors[i % colors.length], 0.8)), bx + w / 2, 0.055 + h / 2, z);
    bx += w + 0.004;
  }
  plush(room, x + 0.33, 0.055, z, "#c79a6f");
  plush(room, x - 0.28, 0.435, z, "#a9b9c9");
  for (const [dx, h, c] of [[0.05, 0.09, "#e2c279"], [0.17, 0.07, "#8fb3a9"], [0.11, 0.06, "#d48f86"]]) {
    place(room, soft(h, h, h, 0.012, std(c, 0.7)), x + dx, 0.435 + h / 2 + (c === "#d48f86" ? 0.09 : 0), z);
  }
}

function armchair(room) {
  const fabric = std("#a9c4bb", 1), cushion = std("#bcd3ca", 1), foot = std("#b58f66", 0.6);
  const chair = new THREE.Group();
  place(chair, soft(0.62, 0.17, 0.56, 0.05, fabric), 0, 0.24, -0.02);
  place(chair, soft(0.44, 0.08, 0.46, 0.035, cushion), 0, 0.365, 0.01);
  place(chair, soft(0.62, 0.62, 0.13, 0.055, fabric), 0, 0.5, -0.27);
  place(chair, soft(0.4, 0.3, 0.07, 0.03, cushion), 0, 0.57, -0.19);
  for (const s of [-1, 1]) {
    place(chair, soft(0.1, 0.34, 0.54, 0.045, fabric), 0.285 * s, 0.37, -0.02);
    for (const z of [-0.24, 0.2]) place(chair, cylinder(0.018, 0.012, 0.16, foot, 12), 0.25 * s, 0.08, z);
  }
  room.add(chair);
}

function sideTable(room) {
  const wood = std("#dcc3a1", 0.6);
  const table = new THREE.Group();
  place(table, cylinder(0.33, 0.33, 0.03, wood, 48), 0, 0.4, 0);
  place(table, cylinder(0.03, 0.04, 0.38, wood, 16), 0, 0.2, 0);
  place(table, cylinder(0.17, 0.19, 0.02, wood, 32), 0, 0.012, 0);
  // tissues and a glass of water: what is actually offered to a child in the room
  place(table, soft(0.2, 0.08, 0.11, 0.012, std("#e9eef0", 0.8)), -0.08, 0.455, 0.03).rotation.y = 0.3;
  place(table, soft(0.05, 0.03, 0.035, 0.012, std("#ffffff", 1)), -0.08, 0.5, 0.03).rotation.y = 0.3;
  const glass = new THREE.MeshStandardMaterial({ color: "#dceef5", transparent: true, opacity: 0.45, roughness: 0.08 });
  place(table, cylinder(0.034, 0.029, 0.1, glass, 20), 0.15, 0.466, -0.05, { cast: false });
  table.position.set(-0.98, 0, 0.42);
  room.add(table);
}

function plant(room) {
  const x = -0.42 - 0.46, z = WALL_Z + 0.3;
  place(room, cylinder(0.14, 0.1, 0.24, std("#d9b49a", 0.8), 24), x, 0.12, z);
  place(room, cylinder(0.125, 0.125, 0.01, std("#5b4a3c", 1), 24), x, 0.238, z, { cast: false });
  const leaf = std("#7ea487", 0.8);
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2, tilt = 0.28 + (i % 3) * 0.14, length = 0.3 + (i % 2) * 0.08;
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.5, 12, 8), leaf);
    m.scale.set(0.07, length, 0.022);
    const pivot = new THREE.Group();
    pivot.position.set(x, 0.24, z);
    pivot.rotation.set(Math.sin(a) * tilt, a, Math.cos(a) * tilt, "YXZ");
    m.position.y = length / 2;
    m.castShadow = true;
    pivot.add(m);
    room.add(pivot);
  }
}

function lamp(room) {
  const x = -1.72, z = WALL_Z + 0.34, metal = std("#b49a78", 0.45);
  place(room, cylinder(0.12, 0.13, 0.02, metal, 28), x, 0.012, z);
  place(room, cylinder(0.011, 0.011, 1.42, metal, 10), x, 0.72, z);
  const shade = new THREE.MeshStandardMaterial({ color: "#fbeed8", emissive: "#ffd9a6", emissiveIntensity: 0.55, roughness: 0.9, side: THREE.DoubleSide });
  place(room, new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.17, 0.2, 28, 1, true), shade), x, 1.5, z, { cast: false, receive: false });
  const light = new THREE.PointLight("#ffd9ae", 0.7, 3.2, 1.8);
  light.position.set(x, 1.45, z + 0.08);
  room.add(light);
}

function recordingCamera(room) {
  // interviews with minors are filmed: a small, discreet camera on the wall
  const dark = std("#3b4250", 0.45), white = std("#eceae5", 0.6);
  const x = 1.72, y = 1.52, z = WALL_Z + 0.09;
  place(room, box(0.06, 0.08, 0.01, white), x, y + 0.04, WALL_Z + 0.008, { cast: false, receive: false });
  place(room, cylinder(0.01, 0.01, 0.09, white, 10), x, y + 0.035, WALL_Z + 0.05, { cast: false, receive: false }).rotation.x = Math.PI / 2;
  const body = place(room, soft(0.065, 0.058, 0.13, 0.014, white), x, y, z, { cast: false, receive: false });
  body.rotation.set(0.28, -0.42, 0);
  const lens = place(room, cylinder(0.021, 0.024, 0.025, dark, 18), x - 0.03, y - 0.018, z + 0.057, { cast: false, receive: false });
  lens.rotation.set(Math.PI / 2 + 0.28, 0, 0.42);
  place(room, ball(0.0055, new THREE.MeshBasicMaterial({ color: "#e0524a" })), x + 0.012, y + 0.008, z + 0.06, { cast: false, receive: false });
}

export function buildRoom(scene) {
  const room = new THREE.Group();

  const wall = std("#f3e9dc", 1), lower = std("#d7e5df", 1), trim = std("#fbf8f2", 0.6);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(SIDE_X * 2, 8), std("#d9c2a4", 0.75));
  floor.rotation.x = -Math.PI / 2;
  place(room, floor, 0, 0, 1.5, { cast: false });
  const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(SIDE_X * 2, 8), std("#faf7f1", 1));
  ceiling.rotation.x = Math.PI / 2;
  place(room, ceiling, 0, HEIGHT, 1.5, { cast: false, receive: false });

  place(room, new THREE.Mesh(new THREE.PlaneGeometry(SIDE_X * 2, HEIGHT), wall), 0, HEIGHT / 2, WALL_Z, { cast: false });
  place(room, new THREE.Mesh(new THREE.PlaneGeometry(SIDE_X * 2, 0.9), lower), 0, 0.45, WALL_Z + 0.004, { cast: false });
  place(room, box(SIDE_X * 2, 0.03, 0.02, trim), 0, 0.9, WALL_Z + 0.01, { cast: false });
  place(room, box(SIDE_X * 2, 0.09, 0.02, trim), 0, 0.045, WALL_Z + 0.01, { cast: false });
  for (const s of [-1, 1]) {
    const side = new THREE.Mesh(new THREE.PlaneGeometry(8, HEIGHT), wall);
    side.rotation.y = -s * Math.PI / 2;
    place(room, side, s * SIDE_X, HEIGHT / 2, 2.3, { cast: false });
  }

  // round rug under the armchair
  const rug = new THREE.Mesh(new THREE.CircleGeometry(1.25, 72), std("#c8d6d9", 1));
  rug.rotation.x = -Math.PI / 2;
  place(room, rug, 0, 0.006, 0.1, { cast: false });
  const band = new THREE.Mesh(new THREE.RingGeometry(1.02, 1.1, 72), std("#eadfce", 1));
  band.rotation.x = -Math.PI / 2;
  place(room, band, 0, 0.009, 0.1, { cast: false });

  window_(room);
  frame(room, 0.62, 1.62, 0.3, 0.38, drawing(houseDrawing));
  frame(room, 1.08, 1.5, 0.3, 0.38, drawing(rainbowDrawing));
  shelf(room);
  armchair(room);
  sideTable(room);
  plant(room);
  lamp(room);
  recordingCamera(room);

  const warm = new THREE.PointLight("#fff0dc", 0.9, 6, 1.4);
  warm.position.set(0.2, 2.25, 0.9);
  room.add(warm);

  scene.add(room);
  return room;
}
