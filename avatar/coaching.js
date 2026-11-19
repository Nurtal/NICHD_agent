// User view: how the interview is going, from coaching.json (ADR 0004, addendum).
// This file displays what the export decided; it holds no protocol rule.

const ICON = { ok: "✓", watch: "!", alert: "⚠" };
const LEVEL_LABEL = { ok: "conforme", watch: "à surveiller", alert: "écart" };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function chip(tag) {
  const node = el("span", `chip ${tag.level}`);
  node.title = LEVEL_LABEL[tag.level];
  node.append(el("b", null, ICON[tag.level]), ` ${tag.label}`);
  return node;
}

function notice(a, withHint = true) {
  const row = el("div", `notice ${a.level}`);
  row.append(el("b", null, `${ICON[a.level]} ${a.message}`));
  if (withHint) row.append(el("span", null, a.hint));
  return row;
}

export class CoachPanel {
  constructor(data, turns, $) {
    this.data = data;
    this.turns = turns; // performance turns: the sentences themselves
    this.$ = $;
    this.byTurn = new Map(data.turns.map((t) => [t.turn, t]));
    $("factstotal").textContent = data.facts_total;
    $("factsnote").textContent = data.facts_hidden ? "révélés au bilan" : "faits recueillis";
    $("closedebrief").onclick = () => this.hideDebrief();
  }

  showCount(n) {
    const node = this.$("factsfound");
    const text = n == null ? "?" : String(n);
    if (node.textContent !== text && node.textContent !== "—") {
      node.classList.remove("bump");
      void node.offsetWidth; // restart the animation
      node.classList.add("bump");
    }
    node.textContent = text;
    this.$("factsbar").style.width = n == null ? "0" : `${Math.round((100 * n) / Math.max(1, this.data.facts_total))}%`;
  }

  showPhases(index) {
    const seen = new Set(this.turns.slice(0, index + 1).map((t) => this.byTurn.get(t.turn)?.phase));
    const current = this.byTurn.get(this.turns[index].turn);
    const at = this.data.phases.findIndex((p) => p.id === current?.phase);
    const box = this.$("phases");
    box.replaceChildren(...this.data.phases.map((p, i) => {
      const state = i === at ? "now" : seen.has(p.id) ? "done" : i < at ? "skipped" : "";
      const dot = el("span", `step ${state}`);
      dot.title = p.label + (state === "skipped" ? " (sautée)" : "");
      return dot;
    }));
    this.$("phasename").textContent = current?.phase_label ?? "";
  }

  showJournal(index) {
    const rows = this.turns.slice(0, index + 1).map((t, i) => {
      const c = this.byTurn.get(t.turn);
      const row = el("div", `entry${i === index ? " current" : ""}`);
      const head = el("div", "head");
      head.append(el("span", "num", `T${t.turn}`));
      if (c) head.append(chip(c.tag));
      row.append(head, el("div", "said", t.interviewer));
      for (const a of c?.alerts ?? []) row.append(notice(a, i === index)); // advice on the current turn only
      return row;
    });
    const box = this.$("journal");
    box.replaceChildren(...rows);
    box.scrollTop = box.scrollHeight;
  }

  /** The learner has just spoken: tag and alerts appear with the sentence. */
  startTurn(index) {
    this.hideDebrief();
    const c = this.byTurn.get(this.turns[index].turn);
    const previous = index > 0 ? this.byTurn.get(this.turns[index - 1].turn) : null;
    this.showCount(previous ? previous.facts_found : this.data.facts_hidden ? null : 0);
    this.showPhases(index);
    this.showJournal(index);
    this.$("qtag").replaceChildren(...(c ? [chip(c.tag)] : []));
    this.$("qalerts").replaceChildren(...(c?.alerts ?? []).map((a) => notice(a)));
  }

  /** The child has answered: the counter moves only now. */
  endReply(index) {
    this.showCount(this.byTurn.get(this.turns[index].turn)?.facts_found ?? null);
  }

  showDebrief() {
    const d = this.data.debrief, $ = this.$;
    $("dfacts").textContent = `${d.facts_found} / ${d.facts_total}`;
    $("dcentral").textContent = `${d.central_found} / ${d.central_total}`;
    $("dopen").textContent = d.open_ratio == null ? "—" : `${Math.round(100 * d.open_ratio)} %`;
    $("dopendetail").textContent = `${d.open_questions} sur ${d.questions} en phase substantive`;
    $("dfalse").textContent = d.false_details;
    $("dissues").replaceChildren(...d.issues.map((text) => el("li", null, text)));
    $("dissuesbox").style.display = d.issues.length ? "" : "none";
    $("debrief").classList.add("open");
  }

  hideDebrief() { this.$("debrief").classList.remove("open"); }
}
