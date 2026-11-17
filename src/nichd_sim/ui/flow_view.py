"""System map (demonstration): the turn's workflow as a graph whose nodes light up live.

Blue = deterministic rules, violet = LLM calls, dashed = data. A turn walks the map: learner's
utterance → classifier (LLM) → phase tracker → behavior engine (phase effects, disclosure gate,
concealment, rule by question type, decision, delivery, body, stage direction) → realizer (LLM)
→ output filter (retry, fallback) → child's reply → log. Only the path actually taken lights up.

`FlowState` is fed by the session's step listener (`Session.turn(on_step=…)`) while the turn runs,
or rebuilt from a logged turn afterwards. Rendering is a pure function: FlowState → HTML/SVG.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from html import escape

from nichd_sim.classification import QuestionType
from nichd_sim.demeanor import CUE_LABELS, stage_direction
from nichd_sim.engine import Decision, EngineState, SpeechAct
from nichd_sim.feedback import PHASE_LABELS, TYPE_LABELS
from nichd_sim.phases import Phase
from nichd_sim.session import TurnRecord
from nichd_sim.ui.engine_view import SPEECH_ACT_LABELS

LEVELS = {"idle": 0, "classify": 1, "classified": 2, "decided": 3, "realize": 4, "filtered": 5, "fallback": 6, "done": 7}

RULES: list[tuple[str, tuple[QuestionType, ...]]] = [
    ("Invitation", (QuestionType.INVITATION,)),
    ("Invitation indicée", (QuestionType.CUED_INVITATION,)),
    ("Facilitateur", (QuestionType.FACILITATOR,)),
    ("Directive", (QuestionType.DIRECTIVE,)),
    ("Choix / oui-non", (QuestionType.OPTION_POSING,)),
    ("Suggestive", (QuestionType.SUGGESTIVE,)),
    ("Soutien / règle", (QuestionType.SUPPORT, QuestionType.GROUND_RULE)),
    ("Autre", (QuestionType.OTHER,)),
]
RULE_COLORS = ["#2e7d32", "#43a047", "#7cb342", "#f9a825", "#ef6c00", "#c62828", "#5e35b1", "#757575"]

GAUGES = [  # same fixed colors as the live engine view (validated categorical slots)
    ("arousal", "Activation", "#2a78d6"),
    ("reluctance", "Réticence", "#eb6834"),
    ("concealment", "Dissimulation", "#1baf7a"),
    ("acquiescence", "Acquiescement", "#eda100"),
    ("verbosity", "Verbosité", "#e87ba4"),
]


@dataclass
class FlowState:
    """What is known of the current turn, step by step."""

    level: int = 0
    utterance: str = ""
    classification: object | None = None
    decision: Decision | None = None
    phase: Phase | None = None
    violations: list = field(default_factory=list)
    state_before: EngineState | None = None
    state_after: EngineState | None = None
    attempts: list[bool] = field(default_factory=list)
    """Verdict of each realization attempt (True: accepted by the output filter)."""
    realizing: int = 0
    fallback: bool = False
    response: str = ""
    deception: bool = False

    def on_step(self, step: str, data: dict) -> None:
        """Feed with `Session.turn(on_step=…)` events."""
        self.level = max(self.level, LEVELS[step])
        if step == "classify":
            self.utterance = data["utterance"]
        elif step == "classified":
            self.classification = data["classification"]
        elif step == "decided":
            self.decision = data["decision"]
            self.phase = data["phase"]
            self.violations = data["violations"]
            self.state_before, self.state_after = data["state_before"], data["state_after"]
        elif step == "realize":
            self.realizing = data["attempt"]
            self.level = LEVELS["realize"]
        elif step == "filtered":
            self.attempts.append(data["ok"])
            self.level = LEVELS["filtered"]
        elif step == "fallback":
            self.fallback = True
        elif step == "done":
            self.response = data["result"].response

    @classmethod
    def from_record(cls, turn: TurnRecord, violations: list, deception: bool) -> FlowState:
        return cls(
            level=LEVELS["done"], utterance=turn.utterance, classification=turn.classification,
            decision=turn.decision, phase=turn.phase, violations=[v for v in violations if v.turn == turn.index],
            state_before=turn.state_before, state_after=turn.state_after,
            attempts=[a.ok for a in turn.attempts], realizing=len(turn.attempts),
            fallback=turn.fallback_used, response=turn.response, deception=deception,
        )


# -- geometry -------------------------------------------------------------------------

W, H = 1200, 690
CHIP_Y0, CHIP_STEP, CHIP_H = 176, 30, 24


def _cut(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


@dataclass
class Node:
    id: str
    x: float
    y: float
    w: float
    h: float
    kind: str  # det | llm | io | data | core | side
    title: str
    sub: str = ""


def _nodes(s: FlowState) -> list[Node]:
    c, d = s.classification, s.decision
    clf_sub = ""
    if c is not None:
        clf_sub = TYPE_LABELS[c.type] + (f" → {c.target}" if c.target else "")
    phase_sub = PHASE_LABELS[s.phase] if s.phase else ""
    if s.violations:
        phase_sub = "⚠ écart au protocole"
    conceal_sub = "—"
    if d is not None:
        if d.retraction is not None:
            conceal_sub = f"revient sur {d.retraction.protected}"
        elif d.lie is not None:
            conceal_sub = f"{d.lie.kind} · {d.lie.protected}"
        elif d.withheld:
            conceal_sub = f"omission · {', '.join(d.withheld)}"
    decision_sub = ""
    if d is not None:
        decision_sub = f"acte : {SPEECH_ACT_LABELS[d.speech_act]} · {len(d.allowed_units)} unité(s) autorisée(s)"
    delivery_sub = body_sub = stage_sub = ""
    if d is not None and d.delivery is not None:
        delivery_sub = f"silence {d.delivery.onset_ms / 1000:.1f} s".replace(".", ",")
        if d.delivery.volume != "normal":
            delivery_sub += " · voix basse" if d.delivery.volume == "low" else " · chuchote"
    if d is not None and d.demeanor is not None and d.demeanor.cues:
        body_sub = CUE_LABELS[d.demeanor.cues[0].cue]
        stage_sub = stage_direction(d.demeanor, d.delivery, silent=d.speech_act == SpeechAct.SILENCE,
                                    text=s.response or None)
    real_sub = f"essai {s.realizing}" if s.realizing else ""
    filt_sub = ""
    if s.attempts:
        filt_sub = "accepté" if s.attempts[-1] else f"rejeté (essai {len(s.attempts)})"
    nodes = [
        Node("input", 20, 20, 170, 64, "io", "Énoncé de l'apprenant", f"« {_cut(s.utterance, 24)} »" if s.utterance else ""),
        Node("clf", 225, 20, 200, 64, "llm", "Classifieur (LLM)", clf_sub or "skill NICHD, JSON contraint"),
        Node("phases", 460, 20, 190, 64, "det", "Suivi des phases", phase_sub or "machine à états"),
        Node("effects", 40, 200, 150, 56, "det", "Effets de phase", "soutien, rapport, règles"),
        Node("gate", 210, 200, 180, 56, "det", "Porte de dévoilement", "pression / seuil"),
        Node("conceal", 410, 200, 160, 56, "det", "Dissimulation", conceal_sub if s.deception else "pas de secret"),
        Node("disclosure", 210, 300, 180, 34, "side", "Dévoilement", ""),
        Node("contamination", 410, 300, 160, 34, "side", "Contamination", ""),
        Node("decision", 840, 186, 320, 76, "core", "Décision", decision_sub),
        Node("delivery", 840, 356, 150, 56, "det", "Diction", delivery_sub),
        Node("body", 1010, 356, 150, 56, "det", "Corps", body_sub),
        Node("stage", 880, 448, 290, 46, "det", "Didascalie", stage_sub or "gabarit"),
        Node("realizer", 40, 566, 210, 60, "llm", "Réalisateur (LLM)", real_sub or "ne voit que les unités autorisées"),
        Node("filter", 290, 566, 180, 60, "det", "Filtre de sortie", filt_sub or "lexique + contrôle de fuite"),
        Node("fallback", 300, 640, 160, 36, "side", "Réponse type (repli)", ""),
        Node("output", 520, 566, 450, 60, "io", "Réponse de l'enfant", f"« {s.response} »" if s.response else ""),
        Node("log", 1010, 566, 170, 60, "data", "Journal de session", "rejouable"),
    ]
    for i, (label, _) in enumerate(RULES):
        nodes.append(Node(f"rule{i}", 600, CHIP_Y0 + i * CHIP_STEP, 190, CHIP_H, "chip", label))
    return nodes


def _rule_index(d: Decision | None) -> int | None:
    if d is None or d.speech_act in (SpeechAct.RELUCTANT, SpeechAct.RETRACT) or d.effective_type is None:
        return None  # the gate or a retraction answered before any rule
    for i, (_, types) in enumerate(RULES):
        if d.effective_type in types:
            return i
    return None


def lit_nodes(s: FlowState) -> list[str]:
    """Lit nodes, in walking order."""
    return _lit(s)[0]


def _lit(s: FlowState) -> tuple[list[str], set[str]]:
    """Lit nodes in walking order, and busy ones (pulsing: an LLM is working)."""
    order: list[str] = []
    busy: set[str] = set()
    d, c = s.decision, s.classification
    if s.level >= 1:
        order.append("input")
    if s.level == 1:
        busy.add("clf")
    if s.level >= 2:
        order.append("clf")
    if s.level >= 3 and d is not None:
        order += ["phases", "state"]
        hint = c.phase_hints[0] if c is not None and c.phase_hints else None
        t = d.effective_type or (c.type if c else None)
        if t in (QuestionType.SUPPORT, QuestionType.GROUND_RULE) or (
            t in (QuestionType.INVITATION, QuestionType.CUED_INVITATION) and hint in ("rapport", "narrative_practice")
        ):
            order.append("effects")
        if d.speech_act == SpeechAct.RELUCTANT or d.disclosure:
            order.append("gate")
        if d.lie is not None or d.withheld or d.retraction is not None:
            order.append("conceal")
        rule = _rule_index(d)
        if rule is not None:
            order.append(f"rule{rule}")
        if d.disclosure:
            order.append("disclosure")
        if d.new_contamination:
            order.append("contamination")
        order += ["decision", "delivery", "body", "stage"]
    if s.realizing:
        order.append("realizer")
        if s.level == LEVELS["realize"]:
            busy.add("realizer")
    if s.attempts:
        order.append("filter")
    if s.fallback:
        order.append("fallback")
    if s.level >= LEVELS["done"]:
        order += ["output", "log"]
    return order, busy


EDGES: list[tuple[str, str, str, str]] = [
    # (id, from, to, svg path)
    ("e_in", "input", "clf", "M190,52 L225,52"),
    ("e_clf", "clf", "phases", "M425,52 L460,52"),
    ("e_ph", "phases", "engine", "M555,84 L555,122 L115,122 L115,200"),
    ("e_eff", "effects", "gate", "M190,228 L210,228"),
    ("e_gate", "gate", "conceal", "M390,228 L410,228"),
    ("e_disc", "gate", "disclosure", "M300,256 L300,300"),
    ("e_dec", "decision", "delivery", "M915,262 L915,356"),
    ("e_body", "decision", "body", "M1085,262 L1085,356"),
    ("e_st1", "delivery", "stage", "M915,412 L915,448"),
    ("e_st2", "body", "stage", "M1085,412 L1085,448"),
    ("e_real", "decision", "realizer", "M840,250 L822,250 L822,540 L145,540 L145,566"),
    ("e_filt", "realizer", "filter", "M250,596 L290,596"),
    ("e_out", "filter", "output", "M470,596 L520,596"),
    ("e_retry", "filter", "realizer", "M330,626 L330,634 L145,634 L145,626"),
    ("e_fb", "filter", "fallback", "M380,626 L380,640"),
    ("e_fbo", "fallback", "output", "M460,658 L745,658 L745,626"),
    ("e_stout", "stage", "output", "M1000,494 L1000,530 L900,530 L900,566"),
    ("e_log", "output", "log", "M970,596 L1010,596"),
    ("e_state", "state", "engine", "M935,130 L935,150"),
]


def _edge_on(eid: str, a: str, b: str, lit: set[str], s: FlowState) -> bool:
    if eid == "e_ph":
        return "phases" in lit and s.decision is not None
    if eid == "e_state":
        return "state" in lit
    if eid == "e_eff":
        return "effects" in lit and "gate" in lit
    if eid == "e_gate":
        return "gate" in lit and "conceal" in lit
    if eid == "e_retry":
        return len(s.attempts) >= 2 or (len(s.attempts) == 1 and not s.attempts[0])
    if eid == "e_out":
        return "output" in lit and not s.fallback
    if eid == "e_stout":
        return "output" in lit
    return a in lit and b in lit


def _rule_edges(lit: set[str]) -> list[tuple[str, str, bool]]:
    """Fan from the gates into each rule chip, and from each chip to the decision."""
    out = []
    for i in range(len(RULES)):
        cy = CHIP_Y0 + i * CHIP_STEP + CHIP_H / 2
        on = f"rule{i}" in lit
        out.append((f"e_r{i}a", f"M570,228 L582,228 L582,{cy} L600,{cy}", on))
        out.append((f"e_r{i}b", f"M790,{cy} L810,{cy} L810,224 L840,224", on))
    return out


# -- rendering ------------------------------------------------------------------------

CSS = """
<style>
.nichd-flow { font-family:"Source Sans 3","Segoe UI",system-ui,sans-serif; }
.nichd-flow .bg { fill:#ffffff; stroke:#dfe3ea; }
.nichd-flow .n rect { stroke-width:1.6; transition:opacity .3s; }
.nichd-flow .n { opacity:.28; }
.nichd-flow .n.on { opacity:1; }
.nichd-flow .n.on.fresh { animation:nf-pop .45s ease-out both; animation-delay:var(--d); }
.nichd-flow .n.on rect { filter:drop-shadow(0 0 5px var(--glow)); }
.nichd-flow .n.busy { opacity:1; animation:nf-pulse 1s ease-in-out infinite; }
.nichd-flow .n.busy rect { filter:drop-shadow(0 0 9px var(--glow)); }
.nichd-flow .det rect { fill:#e6eef8; stroke:#1f4e8c; } .nichd-flow .det { --glow:#1f4e8c; }
.nichd-flow .core rect { fill:#e6eef8; stroke:#1f4e8c; stroke-width:3; } .nichd-flow .core { --glow:#1f4e8c; }
.nichd-flow .llm rect { fill:#f1ebfa; stroke:#5e35b1; } .nichd-flow .llm { --glow:#5e35b1; }
.nichd-flow .io rect { fill:#ffffff; stroke:#1c2230; } .nichd-flow .io { --glow:#1c2230; }
.nichd-flow .data rect { fill:#ffffff; stroke:#8a93a3; stroke-dasharray:5 3; } .nichd-flow .data { --glow:#8a93a3; }
.nichd-flow .side rect { fill:#fdf3e7; stroke:#ef6c00; } .nichd-flow .side { --glow:#ef6c00; }
.nichd-flow .side.bad rect { fill:#fdecea; stroke:#c62828; } .nichd-flow .side.bad { --glow:#c62828; }
.nichd-flow .side.good rect { fill:#e8f5e9; stroke:#2e7d32; } .nichd-flow .side.good { --glow:#2e7d32; }
.nichd-flow .chip rect { stroke:none; }
.nichd-flow .chip text { fill:#ffffff; font-weight:600; }
.nichd-flow text { fill:#1c2230; font-size:13px; }
.nichd-flow text.t { font-size:14px; font-weight:700; }
.nichd-flow .llm text.t { fill:#5e35b1; }
.nichd-flow text.s { font-size:11.5px; fill:#5b6475; }
.nichd-flow text.lbl { font-size:12px; fill:#1f4e8c; font-weight:700; letter-spacing:.06em; }
.nichd-flow text.k { font-size:11px; fill:#5b6475; }
.nichd-flow .e { fill:none; stroke:#c5ccd8; stroke-width:1.5; }
.nichd-flow .e.on { stroke:#1f4e8c; stroke-width:2.4; stroke-dasharray:7 5;
  animation:nf-flow .7s linear infinite; }
.nichd-flow .e.on.llm-e { stroke:#5e35b1; }
.nichd-flow .e.on.bad-e { stroke:#c62828; }
.nichd-flow .panel { fill:#f7f9fc; stroke:#c9d3e3; stroke-width:1.4; }
.nichd-flow rect.g { stroke:none; filter:none !important; }
@keyframes nf-pop { 0% { opacity:.28; transform:scale(.96); } 60% { opacity:1; transform:scale(1.04); }
  100% { opacity:1; transform:scale(1); } }
.nichd-flow .n.on.fresh { transform-box:fill-box; transform-origin:center; }
@keyframes nf-pulse { 0%,100% { opacity:1; } 50% { opacity:.55; } }
@keyframes nf-flow { to { stroke-dashoffset:-12; } }
@media (prefers-reduced-motion: reduce) {
  .nichd-flow .n.on.fresh, .nichd-flow .n.busy, .nichd-flow .e.on { animation:none; }
}
</style>
"""


def _gauges(s: FlowState, on: bool) -> str:
    before, after = s.state_before, s.state_after
    rows = [g for g in GAUGES if g[0] != "concealment" or s.deception]
    parts = [f"<g class='n data {'on' if on else ''}'>",
             "<rect class='frame' x='690' y='10' width='490' height='120' rx='12'/>",
             "<text class='t' x='706' y='32'>État interne de l'enfant</text>"]
    if before is not None and after is not None:
        parts.append(f"<text class='k' x='1166' y='32' text-anchor='end'>tour {after.turn}</text>")
    for i, (name, label, color) in enumerate(rows):
        y = 44 + i * 16
        parts.append(f"<text class='s' x='706' y='{y + 10}'>{label}</text>")
        parts.append(f"<rect class='g' x='810' y='{y + 2}' width='280' height='9' rx='4' style='fill:#edf0f5'/>")
        if after is not None:
            v = getattr(after, name)
            parts.append(f"<rect class='g' x='810' y='{y + 2}' width='{280 * v:.1f}' height='9' rx='4' style='fill:{color}'/>")
            delta = v - getattr(before, name) if before is not None else 0.0
            sign = "▲" if delta > 0.004 else "▼" if delta < -0.004 else ""
            parts.append(f"<text class='s' x='1100' y='{y + 10}'>{v:.2f} {sign}"
                         f"{f'{abs(delta):.2f}' if sign else ''}</text>")
    parts.append("</g>")
    return "".join(parts)


def render(s: FlowState, fresh: set[str] | None = None) -> str:
    """HTML for st.html: the map as a self-contained SVG image. Streamlit's HTML sanitizer drops
    inline SVG; an image keeps it whole, CSS animations included."""
    data = base64.b64encode(render_svg(s, fresh).encode("utf-8")).decode("ascii")
    return f"<img alt='Carte du système' style='width:100%;display:block' src='data:image/svg+xml;base64,{data}'/>"


def render_svg(s: FlowState, fresh: set[str] | None = None) -> str:
    """The map, standalone SVG. `fresh`: nodes that just lit up (animated in walking order)."""
    order, busy = _lit(s)
    lit = set(order)
    if fresh is None:
        fresh = lit
    delay = {nid: i * 0.12 for i, nid in enumerate(n for n in order if n in fresh)}
    nodes = _nodes(s)
    d = s.decision
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' class='nichd-flow' viewBox='0 0 {W} {H}' width='{W}' height='{H}' "
           "role='img' aria-label='Carte du système : chemin du dernier tour'>", CSS,
           f"<rect class='bg' x='0.5' y='0.5' width='{W - 1}' height='{H - 1}' rx='14'/>"]
    # engine panel
    out.append("<rect class='panel' x='20' y='150' width='1160' height='366' rx='14'/>")
    out.append("<text class='lbl' x='40' y='174'>MOTEUR DE COMPORTEMENT — déterministe, graine fixée</text>")
    out.append("<text class='k' x='600' y='170'>règle par type de question</text>")
    # edges (under nodes)
    for eid, a, b, path in EDGES:
        on = _edge_on(eid, a, b, lit, s)
        extra = " llm-e" if eid in ("e_in", "e_clf", "e_real", "e_filt") else ""
        extra += " bad-e" if eid in ("e_retry", "e_fb", "e_fbo") else ""
        out.append(f"<path class='e{' on' if on else ''}{extra}' d='{path}'/>")
    for eid, path, on in _rule_edges(lit):
        out.append(f"<path class='e{' on' if on else ''}' d='{path}'/>")
    out.append("<text class='k' x='160' y='536'>unités autorisées seulement</text>")
    # nodes
    out.append(_gauges(s, "state" in lit))
    for n in nodes:
        classes = ["n", "chip" if n.kind == "chip" else n.kind]
        if n.id in lit:
            classes.append("on")
            if n.id in fresh:
                classes.append("fresh")
        if n.id in busy:
            classes.append("busy")
        if n.id == "disclosure" and d is not None and d.forced_disclosure:
            classes.append("bad")
        elif n.id == "disclosure":
            classes.append("good")
        if n.id in ("contamination", "fallback"):
            classes.append("bad")
        style = f" style='--d:{delay.get(n.id, 0):.2f}s'"
        out.append(f"<g class='{' '.join(classes)}'{style}>")
        if n.kind == "chip":
            i = int(n.id[4:])
            out.append(f"<rect x='{n.x}' y='{n.y}' width='{n.w}' height='{n.h}' rx='12' fill='{RULE_COLORS[i]}'/>")
            out.append(f"<text x='{n.x + 12}' y='{n.y + 16.5}'>{escape(n.title)}</text>")
        else:
            out.append(f"<rect x='{n.x}' y='{n.y}' width='{n.w}' height='{n.h}' rx='10'/>")
            ty = n.y + (22 if n.h > 40 else n.h / 2 + 5)
            out.append(f"<text class='t' x='{n.x + 12}' y='{ty}'>{escape(n.title)}</text>")
            if n.sub and n.h > 40:
                out.append(f"<text class='s' x='{n.x + 12}' y='{n.y + 42}'>{escape(_cut(n.sub, int(n.w / 6.3)))}</text>")
        out.append("</g>")
    if d is not None:
        out.append(f"<text class='s' x='856' y='{186 + 66}'>{escape(_cut(d.reason, 52))}</text>")
    out.append("</svg>")
    return "".join(out)
