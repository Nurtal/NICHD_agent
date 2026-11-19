// Continuous body surfaces: a tube through control points, closed by domes, optionally skinned to bones so
// that it bends at the joints (shoulder, elbow, hip, knee, neck) instead of showing juxtaposed volumes.
import * as THREE from "three";

const SIDE = new THREE.Vector3(1, 0, 0);

/**
 * points: [{ at: Object3D, p: [x, y, z] in `at`'s frame, r: [across, normal], w: {boneIndex: weight} }]
 * The geometry is in `owner`'s frame, built from the frames' current world matrices (the bind pose).
 * bumps: [{ t, dir: Vector3 (owner frame), amp, width (along t), spread (around the ring) }].
 * groupAt(t, centre) → material index, for parts lit separately in the dev view.
 */
export function tubeGeometry(owner, points, { rings = 48, sides = 26, dome = 4, bumps = [], groupAt = null, skinned = true } = {}) {
  owner.updateWorldMatrix(true, false);
  const toOwner = owner.matrixWorld.clone().invert();
  const centres = points.map((q) => {
    q.at.updateWorldMatrix(true, false);
    return new THREE.Vector3(...q.p).applyMatrix4(q.at.matrixWorld).applyMatrix4(toOwner);
  });
  const curve = new THREE.CatmullRomCurve3(centres, false, "catmullrom", 0.5);
  const n = points.length;
  const sample = (t) => { // radii and weights, linear between control points (uniform in t like the curve)
    const s = Math.min(n - 1.0001, Math.max(0, t * (n - 1)));
    const k = Math.floor(s), f = s - k, a = points[k], b = points[k + 1];
    const w = {};
    for (const [i, v] of Object.entries(a.w || {})) w[i] = (w[i] || 0) + v * (1 - f);
    for (const [i, v] of Object.entries(b.w || {})) w[i] = (w[i] || 0) + v * f;
    return { r: [a.r[0] + (b.r[0] - a.r[0]) * f, a.r[1] + (b.r[1] - a.r[1]) * f], w };
  };

  // rings: start dome, body, end dome; each {c, T, B, N, r, w, t, scale}
  const list = [];
  const frameAt = (t) => {
    const T = curve.getTangent(Math.min(1, Math.max(0, t))).normalize();
    const B = SIDE.clone().addScaledVector(T, -SIDE.dot(T)).normalize();
    return { T, B, N: new THREE.Vector3().crossVectors(T, B) };
  };
  const domeRings = (t, sign) => {
    const out = [];
    const { T, B, N } = frameAt(t), s = sample(t), c = curve.getPoint(t);
    const depth = 0.9 * Math.min(s.r[0], s.r[1]);
    for (let j = 1; j <= dome; j++) {
      const phi = (j / (dome + 1)) * (Math.PI / 2);
      out.push({ c: c.clone().addScaledVector(T, sign * depth * Math.sin(phi)), T, B, N, r: s.r, w: s.w, t, scale: Math.cos(phi) });
    }
    return { rings: out, apex: c.clone().addScaledVector(T, sign * depth), w: s.w };
  };
  const startCap = domeRings(0, -1), endCap = domeRings(1, 1);
  list.push(...startCap.rings.reverse());
  for (let i = 0; i <= rings; i++) {
    const t = i / rings, s = sample(t);
    list.push({ c: curve.getPoint(t), ...frameAt(t), r: s.r, w: s.w, t, scale: 1 });
  }
  list.push(...endCap.rings);

  const pos = [], skinIndex = [], skinWeight = [];
  const pushWeights = (w) => {
    const top = Object.entries(w).filter(([, v]) => v > 1e-4).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const total = top.reduce((sum, [, v]) => sum + v, 0) || 1;
    for (let k = 0; k < 4; k++) {
      skinIndex.push(top[k] ? Number(top[k][0]) : 0);
      skinWeight.push(top[k] ? top[k][1] / total : 0);
    }
  };
  const u = new THREE.Vector3(), v = new THREE.Vector3();
  for (const ring of list) {
    for (let a = 0; a < sides; a++) {
      const ang = (a / sides) * Math.PI * 2;
      u.copy(ring.B).multiplyScalar(Math.cos(ang) * ring.r[0]).addScaledVector(ring.N, Math.sin(ang) * ring.r[1]);
      const radial = v.copy(u).normalize();
      let grow = 0;
      for (const bump of bumps) {
        const along = Math.exp(-((ring.t - bump.t) ** 2) / (2 * bump.width ** 2));
        const around = Math.exp(-(1 - radial.dot(bump.dir)) / (bump.spread ?? 0.25));
        grow += bump.amp * along * around;
      }
      u.multiplyScalar(ring.scale).addScaledVector(radial, grow * ring.scale);
      pos.push(ring.c.x + u.x, ring.c.y + u.y, ring.c.z + u.z);
      pushWeights(ring.w);
    }
  }
  const startApex = pos.length / 3;
  pos.push(startCap.apex.x, startCap.apex.y, startCap.apex.z);
  pushWeights(startCap.w);
  const endApex = pos.length / 3;
  pos.push(endCap.apex.x, endCap.apex.y, endCap.apex.z);
  pushWeights(endCap.w);

  const byGroup = new Map();
  const tri = (g, a, b, c) => { if (!byGroup.has(g)) byGroup.set(g, []); byGroup.get(g).push(a, b, c); };
  const group = (ring) => (groupAt ? groupAt(ring.t, ring.c) : 0);
  for (let i = 0; i < list.length - 1; i++) {
    const g = group(list[i].t < 0.5 ? list[i + 1] : list[i]);
    for (let a = 0; a < sides; a++) {
      const a2 = (a + 1) % sides;
      const p0 = i * sides + a, p1 = i * sides + a2, q0 = (i + 1) * sides + a, q1 = (i + 1) * sides + a2;
      tri(g, p0, p1, q0); // outward: T × (B → N) points inside, so the order is reversed
      tri(g, p1, q1, q0);
    }
  }
  const last = (list.length - 1) * sides;
  for (let a = 0; a < sides; a++) {
    const a2 = (a + 1) % sides;
    tri(group(list[0]), startApex, a2, a);
    tri(group(list[list.length - 1]), endApex, last + a, last + a2);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  if (skinned) {
    geo.setAttribute("skinIndex", new THREE.Uint16BufferAttribute(skinIndex, 4));
    geo.setAttribute("skinWeight", new THREE.Float32BufferAttribute(skinWeight, 4));
  }
  const index = [];
  for (const g of [...byGroup.keys()].sort((a, b) => a - b)) {
    geo.addGroup(index.length, byGroup.get(g).length, g);
    index.push(...byGroup.get(g));
  }
  geo.setIndex(index);
  geo.computeVertexNormals();
  return geo;
}

/** A skinned mesh bound to `bones` in their current pose. `materials` may be an array (one per group). */
export function skinnedMesh(owner, geometry, materials, bones) {
  const mesh = new THREE.SkinnedMesh(geometry, materials);
  owner.add(mesh);
  mesh.updateMatrixWorld(true);
  mesh.bind(new THREE.Skeleton(bones));
  mesh.castShadow = true;
  mesh.frustumCulled = false; // the bind-pose bounds do not follow the bones
  return mesh;
}

/** Direction from a bent joint outward (elbow point, kneecap): `before` → `joint` → `after`, in owner frame. */
export function outerCorner(before, joint, after) {
  const d1 = joint.clone().sub(before).normalize(), d2 = after.clone().sub(joint).normalize();
  return d1.sub(d2).normalize();
}

/** A control point's position in `owner`'s frame (for bump directions). */
export function inOwner(owner, at, p) {
  owner.updateWorldMatrix(true, false);
  at.updateWorldMatrix(true, false);
  return new THREE.Vector3(...p).applyMatrix4(at.matrixWorld).applyMatrix4(owner.matrixWorld.clone().invert());
}
