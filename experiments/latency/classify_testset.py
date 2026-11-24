"""Classify the skill's test set once per thinking level and keep every prediction (lot L1).

    uv run python experiments/latency/classify_testset.py off medium

Writes results/testset_<think>.jsonl (prediction, latency, thinking tokens), so escalation rules for the cascade can be
compared offline (cascade.py) without calling the model again. One model, unloaded at the end."""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

from nichd_sim.classification import ClassificationContext
from nichd_sim.classifiers.llm import LLMClassifier
from nichd_sim.cli import parse_think
from nichd_sim.evaluation import NEW_FIELDS, _value, load_scenarios, load_testset
from nichd_sim.llm import DEFAULT_MODEL, DEFAULT_URL, OllamaClient

OUT = Path(__file__).parent / "results"


def main(levels: list[str]) -> None:
    items = load_testset()
    scenarios = load_scenarios()
    client = OllamaClient(DEFAULT_MODEL, keep_alive="10m", timeout=300)
    for level in levels:
        clf = LLMClassifier(client, think=parse_think(level))
        path = OUT / f"testset_{level}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for k, item in enumerate(items, 1):
                ctx = ClassificationContext(scenario=scenarios[item["scenario"]], revealed_unit_ids=list(item["already_said"]))
                t = time.perf_counter()
                c = clf.classify(item["utterance"], ctx)
                pred = {"type": c.type.value, "target": c.target,
                        "inner_type": c.inner_type.value if c.inner_type else None,
                        "phase_hint": c.phase_hints[0] if c.phase_hints else None,
                        **{n: _value(getattr(c, n)) for n in NEW_FIELDS}}
                f.write(json.dumps({"id": item["id"], "pred": pred, "latency_s": time.perf_counter() - t,
                                    "eval_count": c.meta.get("eval_count"), "error": c.meta.get("error")},
                                   ensure_ascii=False) + "\n")
                f.flush()
                print(f"{level} {k}/{len(items)}", flush=True)
    req = urllib.request.Request(f"{DEFAULT_URL}/api/generate", data=json.dumps({"model": DEFAULT_MODEL, "keep_alive": 0}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()


if __name__ == "__main__":
    main(sys.argv[1:] or ["off", "medium"])
