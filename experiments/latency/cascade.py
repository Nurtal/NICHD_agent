"""Compare escalation rules for the cascade classifier, offline (lot L1).

    uv run python experiments/latency/cascade.py

    uv run python experiments/latency/cascade.py low   # second pass with low thinking

Reads results/testset_off.jsonl and results/testset_<second>.jsonl (classify_testset.py). A rule escalates an item when
its fast (no-thinking) answer matches; the cascade's answer is then the medium one, and its latency is the sum."""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

from nichd_sim.classification import OUT_OF_SCENARIO
from nichd_sim.evaluation import EvalReport, ItemResult, load_testset

HERE = Path(__file__).parent / "results"


def load(level: str) -> dict[str, dict]:
    return {r["id"]: r for r in map(json.loads, (HERE / f"testset_{level}.jsonl").read_text(encoding="utf-8").splitlines())}


def report(items, preds, name) -> EvalReport:
    rep = EvalReport(model=name, skill_version="")
    for it in items:
        p = preds[it["id"]]
        rep.items.append(ItemResult(id=it["id"], utterance=it["utterance"], gold=it["label"], pred=p["pred"],
                                    ambiguous=it.get("ambiguous", False), latency_s=p["latency_s"]))
    return rep


def rule(types: set[str], out_of_scenario: bool = True):
    def escalate(p: dict) -> bool:
        return bool(p.get("error")) or p["pred"]["type"] in types or (out_of_scenario and p["pred"]["target"] == OUT_OF_SCENARIO)
    return escalate


def main(second: str = "medium") -> None:
    items = load_testset()
    off, med = load("off"), load(second)
    for name, preds in (("off", off), (second, med)):
        r = report(items, preds, name)
        print(f"{name:40s} κ {r.kappa:.3f}  type {r.type_accuracy:.1%}  cible {r.target_accuracy:.1%}  "
              f"lat méd {st.median(p['latency_s'] for p in preds.values()):.1f} s")
    r_off = report(items, off, "off")
    print("\nErreurs du passage rapide (attendu → prédit) :")
    for x in r_off.items:
        if not x.type_ok or (x.gold["target"] is not None and not x.target_ok):
            print(f"  {x.id:8s} {x.gold['type']:16s} → {x.pred['type']:16s} cible {x.gold['target']} → {x.pred['target']}"
                  f"   {x.utterance[:60]}")
    candidates = {
        "suggestive+option": {"suggestive", "option_posing"},
        "+directive": {"suggestive", "option_posing", "directive"},
        "+other": {"suggestive", "option_posing", "other"},
        "+directive+other": {"suggestive", "option_posing", "directive", "other"},
        "+directive+other+compound": {"suggestive", "option_posing", "directive", "other", "compound"},
        "+directive+other+compound+cued": {"suggestive", "option_posing", "directive", "other", "compound",
                                           "cued_invitation"},
        "+directive+other+compound+cued+support": {"suggestive", "option_posing", "directive", "other", "compound",
                                                   "cued_invitation", "support"},
        "tout sauf rapport/soutien": {"suggestive", "option_posing", "directive", "other", "compound", "cued_invitation",
                                      "invitation", "facilitator"},
    }
    print()
    for name, types in candidates.items():
        for oos in (True, False):
            esc = rule(types, oos)
            preds = {i: (med[i] if esc(off[i]) else off[i]) for i in off}
            lat = [off[i]["latency_s"] + (med[i]["latency_s"] if esc(off[i]) else 0) for i in off]
            r = report(items, preds, name)
            share = sum(esc(off[i]) for i in off) / len(off)
            print(f"{name + (' +hors' if oos else ''):40s} κ {r.kappa:.3f}  type {r.type_accuracy:.1%}  cible "
                  f"{r.target_accuracy:.1%}  escalade {share:.0%}  lat méd {st.median(lat):.1f} s  p95 "
                  f"{sorted(lat)[round(0.95 * (len(lat) - 1))]:.1f} s")


if __name__ == "__main__":
    import sys

    main(*sys.argv[1:2])
