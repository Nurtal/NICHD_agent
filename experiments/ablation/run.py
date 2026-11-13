"""Run the ablation: same scripted interviews for the hybrid child and the LLM-only child.

    uv run python experiments/ablation/run.py [--models qwen3.8:latest phi4 ...] [--seeds 0 1 2]

Writes one JSONL line per (condition, scenario, seed) interview, resumable (done runs are skipped).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from protocol import baseline_messages, script, strip_tag  # noqa: E402

from nichd_sim.classifiers.manual import ManualClassifier  # noqa: E402
from nichd_sim.evaluation import load_scenarios  # noqa: E402
from nichd_sim.llm import OllamaClient  # noqa: E402
from nichd_sim.realization import LLMRealizer  # noqa: E402
from nichd_sim.session import Session  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEMPERATURE = 0.7  # same as LLMRealizer's default


def run_hybrid(scenario, seed, client):
    s = Session(scenario, ManualClassifier(), LLMRealizer(client, seed=seed, temperature=TEMPERATURE), seed=seed)
    turns = []
    for i, u in enumerate(script(scenario), 1):
        t0 = time.perf_counter()
        r = s.turn(u)
        turns.append({
            "turn": i, "interviewer": strip_tag(u), "child": r.response,
            "speech_act": r.decision.speech_act, "allowed": [a.id for a in r.decision.allowed_units],
            "fallback": r.fallback_used, "latency_s": round(time.perf_counter() - t0, 2),
        })
    return turns


def run_llm_only(scenario, seed, client, strong=False):
    history, turns = [], []
    for i, u in enumerate(script(scenario), 1):
        text = strip_tag(u)
        t0 = time.perf_counter()
        res = client.chat(baseline_messages(scenario, history, text, strong=strong), temperature=TEMPERATURE,
                          seed=seed * 1000 + i * 10, think=False)
        child = " ".join(res.content.split())
        history += [("interviewer", text), ("child", child)]
        turns.append({"turn": i, "interviewer": text, "child": child, "latency_s": round(time.perf_counter() - t0, 2)})
    return turns


CONDITIONS = {
    "hybrid": run_hybrid,
    "llm_only": run_llm_only,
    "llm_only_strong": lambda sc, seed, client: run_llm_only(sc, seed, client, strong=True),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--out", default=str(ROOT / "experiments/ablation/results"))
    ap.add_argument("--models", nargs="+", default=["qwen3.8:latest"])
    ap.add_argument("--conditions", nargs="+", default=list(CONDITIONS))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "transcripts.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            done.add((d["model"], d["condition"], d["scenario"], d["seed"]))
    scenarios = load_scenarios(ROOT / "scenarios")
    for model in args.models:  # one model at a time: Ollama keeps it loaded
        client = OllamaClient(model)
        for seed in args.seeds:
            for sid, sc in scenarios.items():
                for cond in args.conditions:
                    if (model, cond, sid, seed) in done:
                        continue
                    t0 = time.perf_counter()
                    turns = CONDITIONS[cond](sc, seed, client)
                    rec = {"condition": cond, "scenario": sid, "seed": seed, "model": model, "turns": turns}
                    with path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print(f"{model:16} {cond:16} {sid:26} seed={seed} {time.perf_counter() - t0:6.1f}s", flush=True)


if __name__ == "__main__":
    main()
