// Replays an exported session (performance.json, ADR 0004) on the placeholder child.
// URL options: ?turn=N (start turn), ?autoplay=0, ?at=ms (freeze the reply at that time: screenshots),
// ?map=1 (system map behind the child: debug channel, exported with --debug-map, not in the contract).
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { buildChild, buildScene } from "./figure.js";
import { Animator, FAMILY_COLOR, targetsFor } from "./cues.js";

const QUESTION_MS = 1600; // the interviewer's question shown before the reply's timeline starts
const GAP_MS = 1400; // after the reply, before the next turn (autoplay)

const params = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);

const { renderer, scene, camera, setBackdrop } = buildScene($("scene"));
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.72, 0);
controls.update();
const child = buildChild(scene);
const animator = new Animator(child);

const perf = await (await fetch("/session/performance.json")).json();
document.title = `Avatar — ${perf.child.name}, ${perf.child.age} ans`;
let maps = null; // {turn: [classified, decided, done]} — only when exported with --debug-map
try {
  const r = await fetch("/session/debug/maps.json");
  if (r.ok) maps = await r.json();
} catch { maps = null; }

const state = {
  index: Math.max(0, Math.min(perf.turns.length - 1, (parseInt(params.get("turn") || "1", 10) || 1) - 1)),
  phase: "idle", // idle → question → reply → gap
  phaseStart: 0,
  playing: params.get("autoplay") !== "0",
  audio: null,
  frozenAt: params.has("at") ? parseInt(params.get("at"), 10) : null,
  map: params.get("map") === "1",
  replies: [], // {turn, at}: when each reply started (performance.now), for recordings
  done: false,
};
window.__avatar = state; // for automated screenshots

function turn() { return perf.turns[state.index]; }

function showMap(step) { // 0 classified, 1 decided, 2 done
  const on = state.map && maps != null;
  document.body.classList.toggle("with-map", on);
  $("mapbtn").classList.toggle("on", on);
  setBackdrop(on);
  if (!on) return;
  const files = maps[String(turn().turn)];
  if (files) $("map").src = `/session/debug/${files[Math.min(step, files.length - 1)]}`;
}
if (maps == null) {
  $("mapbtn").disabled = true;
  $("mapbtn").title = "Pas de carte : exporter la session avec --debug-map";
}

function showLegend(t) {
  const rows = (t.body.cues || []).map((c) =>
    `<div class="row"><span class="sw" style="background:${FAMILY_COLOR[c.family] || "#999"}"></span>${c.label || c.cue}</div>`);
  $("cues").innerHTML = rows.join("") || "<div class='row'>Aucun signe (journal ancien)</div>";
  const a = t.body.arousal;
  $("arousalv").textContent = a == null ? "—" : a.toFixed(2);
  $("arousal").style.width = `${Math.round(100 * (a ?? 0))}%`;
  $("style").textContent = t.body.style ? `Style d'expression : ${{ agitated: "agité", frozen: "figé", mixed: "mixte" }[t.body.style]}` : "";
}

function startTurn(i) {
  if (state.audio) { state.audio.pause(); state.audio = null; }
  state.index = i;
  const t = turn();
  $("question").textContent = t.interviewer;
  $("turnlabel").textContent = `Tour ${t.turn} / ${perf.turns.length}`;
  $("stage").textContent = "";
  $("subtitle").innerHTML = "";
  showLegend(t);
  showMap(state.frozenAt != null ? 2 : 0);
  state.phase = "question";
  state.phaseStart = performance.now();
}

function startReply() {
  const t = turn();
  animator.setTargets(targetsFor(t.body, t.voice));
  $("stage").textContent = t.stage_direction ? `(${t.stage_direction})` : "";
  if (state.frozenAt == null) showMap(1);
  state.phase = "reply";
  state.phaseStart = performance.now();
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
    if (ms >= t.duration_ms && state.frozenAt == null) { state.phase = "gap"; state.phaseStart = now; showMap(2); }
  }
  if (state.phase === "gap" && state.playing && now - state.phaseStart > GAP_MS) {
    if (state.index < perf.turns.length - 1) startTurn(state.index + 1);
    else state.done = true;
  }
  animator.update(now / 1000, dt, speaking);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

$("prev").onclick = () => startTurn(Math.max(0, state.index - 1));
$("next").onclick = () => startTurn(Math.min(perf.turns.length - 1, state.index + 1));
$("play").onclick = () => {
  state.playing = !state.playing;
  if (state.audio) state.playing ? state.audio.play() : state.audio.pause();
};
function begin() {
  $("start").style.display = "none";
  startTurn(state.index);
}
$("startbtn").onclick = begin;
$("mapbtn").onclick = () => {
  state.map = !state.map;
  showMap(state.phase === "question" ? 0 : state.phase === "reply" ? 1 : 2);
};
if (state.frozenAt != null || params.get("start") === "1") begin();
requestAnimationFrame(frame);
