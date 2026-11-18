// Replays an exported session (performance.json, ADR 0004), in one of two views:
//   user: the child in the hearing room, with the protocol follow-up (coaching.json);
//   dev:  gaze axis, highlighted body parts, cue legend and system map (debug channel, --debug-map).
// URL options: ?mode=user|dev, ?map=1 (implies dev), ?turn=N (start turn), ?autoplay=0,
// ?at=ms (freeze the reply at that time: screenshots), ?start=1, ?debrief=1 (open the debrief).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { buildChild, buildScene } from "./figure.js";
import { buildRoom } from "./room.js";
import { Animator, FAMILY_COLOR, cuePartsLabel, targetsFor } from "./cues.js";
import { DevOverlay } from "./debug.js";
import { CoachPanel } from "./coaching.js";

const QUESTION_MS = 1600; // the interviewer's question shown before the reply's timeline starts
const GAP_MS = 1400; // after the reply, before the next turn (autoplay)

const params = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);

const { renderer, scene, camera, setView } = buildScene($("scene"));
const controls = new OrbitControls(camera, renderer.domElement);
const child = buildChild(scene);
const room = buildRoom(scene);
const animator = new Animator(child);
const overlay = new DevOverlay(scene, child);

async function optionalJson(url) {
  try {
    const r = await fetch(url);
    return r.ok ? await r.json() : null;
  } catch { return null; }
}

const perf = await (await fetch("/session/performance.json")).json();
document.title = `Avatar — ${perf.child.name}, ${perf.child.age} ans`;
const maps = await optionalJson("/session/debug/maps.json"); // {turn: [classified, decided, done]}
const coachingData = await optionalJson("/session/coaching.json");
const coach = coachingData ? new CoachPanel(coachingData, perf.turns, $) : null;

const state = {
  index: Math.max(0, Math.min(perf.turns.length - 1, (parseInt(params.get("turn") || "1", 10) || 1) - 1)),
  phase: "idle", // idle → question → reply → gap
  phaseStart: 0,
  playing: params.get("autoplay") !== "0",
  audio: null,
  frozenAt: params.has("at") ? parseInt(params.get("at"), 10) : null,
  mode: params.get("map") === "1" || params.get("mode") === "dev" ? "dev" : "user",
  map: params.get("map") !== "0",
  replies: [], // {turn, at}: when each reply started (performance.now), for recordings
  done: false,
};
window.__avatar = state; // for automated screenshots

function turn() { return perf.turns[state.index]; }
function mapStep() { return state.phase === "question" ? 0 : state.phase === "reply" ? 1 : 2; }
function mapOn() { return state.mode === "dev" && state.map && maps != null; }

function showMap(step) { // 0 classified, 1 decided, 2 done
  if (!mapOn() || state.phase === "idle") return;
  const files = maps[String(turn().turn)];
  if (files) $("map").src = `/session/debug/${files[Math.min(step, files.length - 1)]}`;
}

function applyView() {
  const dev = state.mode === "dev", on = mapOn();
  document.body.classList.toggle("mode-dev", dev);
  document.body.classList.toggle("mode-user", !dev);
  document.body.classList.toggle("with-map", on);
  document.body.classList.toggle("with-coach", !dev && coach != null);
  room.visible = !dev;
  child.chair.visible = dev;
  overlay.setVisible(dev);
  $("mapbtn").classList.toggle("on", on);
  $("modebtn").textContent = dev ? "User" : "Dev";
  setView(state.mode, on, controls);
  showMap(mapStep());
}
if (maps == null) {
  $("mapbtn").disabled = true;
  $("mapbtn").title = "Pas de carte : exporter la session avec --debug-map";
}

function showLegend(t) {
  const rows = (t.body.cues || []).map((c) => {
    const parts = cuePartsLabel(c.cue);
    return `<div class="row"><span class="sw" style="background:${FAMILY_COLOR[c.family] || "#999"}"></span>`
      + `<span>${c.label || c.cue}${parts ? `<small> → ${parts}</small>` : ""}</span></div>`;
  });
  $("cues").innerHTML = rows.join("") || "<div class='row'>Aucun signe (journal ancien)</div>";
  const a = t.body.arousal;
  $("arousalv").textContent = a == null ? "—" : a.toFixed(2);
  $("arousal").style.width = `${Math.round(100 * (a ?? 0))}%`;
  $("style").textContent = t.body.style ? `Style d'expression : ${{ agitated: "agité", frozen: "figé", mixed: "mixte" }[t.body.style]}` : "";
}

function showGaze(g) {
  if (!g) return;
  const side = Math.abs(g.yaw) < 1 ? "de face" : `${Math.abs(g.yaw).toFixed(0)}° ${g.yaw > 0 ? "à droite" : "à gauche"}`;
  const height = Math.abs(g.pitch) < 1 ? "à hauteur" : `${Math.abs(g.pitch).toFixed(0)}° ${g.pitch > 0 ? "vers le haut" : "vers le bas"}`;
  $("gaze").textContent = `Regard : ${side}, ${height} (écart à l'interviewer ${g.offset.toFixed(0)}°)`;
}

function startTurn(i) {
  if (state.audio) { state.audio.pause(); state.audio = null; }
  state.index = i;
  const t = turn();
  $("question").textContent = t.interviewer;
  $("turnlabel").textContent = `T${t.turn}/${perf.turns.length}`;
  $("stage").textContent = "";
  $("subtitle").innerHTML = "";
  showLegend(t);
  coach?.startTurn(i);
  state.phase = "question";
  state.phaseStart = performance.now();
  showMap(state.frozenAt != null ? 2 : 0);
}

function startReply() {
  const t = turn();
  animator.setTargets(targetsFor(t.body, t.voice));
  overlay.setCues(t.body.cues);
  $("stage").textContent = t.stage_direction ? `(${t.stage_direction})` : "";
  state.phase = "reply";
  state.phaseStart = performance.now();
  if (state.frozenAt == null) showMap(1);
  else coach?.endReply(state.index);
  state.replies.push({ turn: t.turn, audio: t.audio, at: state.phaseStart });
  if (t.audio && state.frozenAt == null) {
    state.audio = new Audio(`/session/${t.audio}`);
    state.audio.play().catch(() => { state.audio = null; }); // no sound: the internal clock still runs
  }
}

function replyTime(now) {
  if (state.frozenAt != null) return state.frozenAt;
  if (state.audio && !state.audio.paused) return state.audio.currentTime * 1000;
  return now - state.phaseStart;
}

function subtitle(t, ms) {
  let html = "";
  for (const s of t.timeline) {
    if (s.kind !== "speech") continue;
    html += `<span class="${s.start_ms <= ms ? "said" : "todo"}">${s.text.replace(/</g, "&lt;")} </span>`;
  }
  $("subtitle").innerHTML = html;
}

function finish() {
  if (state.done) return;
  state.done = true;
  if (state.mode === "user") coach?.showDebrief();
}

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  let speaking = false;
  const t = turn();
  if (state.phase === "question" && (now - state.phaseStart > QUESTION_MS || state.frozenAt != null)) startReply();
  if (state.phase === "reply") {
    const ms = replyTime(now);
    const span = t.timeline.find((s) => s.start_ms <= ms && ms < s.end_ms);
    speaking = !!span && span.kind === "speech";
    subtitle(t, ms);
    if (ms >= t.duration_ms && state.frozenAt == null) {
      state.phase = "gap";
      state.phaseStart = now;
      showMap(2);
      coach?.endReply(state.index);
    }
  }
  if (state.phase === "gap" && state.playing && now - state.phaseStart > GAP_MS) {
    if (state.index < perf.turns.length - 1) startTurn(state.index + 1);
    else finish();
  }
  animator.update(now / 1000, dt, speaking);
  child.torso.updateWorldMatrix(true, true);
  showGaze(overlay.update(now / 1000, dt, animator.cur.arousal));
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

$("prev").onclick = () => { state.done = false; startTurn(Math.max(0, state.index - 1)); };
$("next").onclick = () => { state.done = false; startTurn(Math.min(perf.turns.length - 1, state.index + 1)); };
$("play").onclick = () => {
  state.playing = !state.playing;
  if (state.audio) state.playing ? state.audio.play() : state.audio.pause();
};
function begin() {
  $("start").style.display = "none";
  startTurn(state.index);
  if (params.get("debrief") === "1") coach?.showDebrief();
}
$("startbtn").onclick = begin;
$("mapbtn").onclick = () => { state.map = !state.map; applyView(); };
$("modebtn").onclick = () => {
  state.mode = state.mode === "dev" ? "user" : "dev";
  coach?.hideDebrief();
  applyView();
};
applyView();
if (state.frozenAt != null || params.get("start") === "1") begin();
requestAnimationFrame(frame);
