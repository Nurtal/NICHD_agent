"""Quick screening of candidate models for the child's voice, before the full ablation.

    uv run python experiments/models/screen.py --priority 1            # screen priority-1 candidates
    uv run python experiments/models/screen.py --models gemma4:31b     # or explicit names
    uv run python experiments/models/screen.py --priority 1 --pull     # download missing ones first

For each model: does it fit entirely in GPU memory, then 7 hybrid interviews (one per scenario,
seed 0) with the output filter's verdicts: fallback rate and rejection reasons, latency, reply
length, role breaks, English words. Resumable (screened models are skipped unless --force).
Writes results/screening.jsonl (one record per model, with transcripts) and results/screening.md.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "experiments/ablation"))

from analyze import ROLE_BREAK  # noqa: E402
from run import load_candidates, make_client, run_hybrid, unload  # noqa: E402

from nichd_sim.evaluation import load_scenarios  # noqa: E402
from nichd_sim.llm import LLMError  # noqa: E402

URL = "http://localhost:11434"
OUT = HERE / "results"
# Frequent English words that never occur as French words in a child's reply.
ENGLISH = {"the", "and", "you", "yes", "what", "with", "this", "that", "okay", "sorry", "i'm", "it's", "don't"}


def api(path: str, body: dict | None = None, timeout: float = 600) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{URL}{path}", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def canonical(name: str) -> str:
    return name if ":" in name.split("/")[-1] else f"{name}:latest"


def installed() -> set[str]:
    return {m["name"] for m in api("/api/tags")["models"]}


def pull(name: str) -> bool:
    print(f"pull {name} …", flush=True)
    return subprocess.run(["ollama", "pull", name]).returncode == 0


def gpu_fit(name: str, options: dict) -> dict:
    """Load the model with the run's context size and read how much of it sits in VRAM."""
    opts = {k: v for k, v in options.items() if k == "num_ctx"}
    t0 = time.perf_counter()
    api("/api/generate", {"model": name, "prompt": "", "keep_alive": "10m", "options": opts})
    load_s = time.perf_counter() - t0
    for m in api("/api/ps")["models"]:
        if m["name"] == name:
            return {"load_s": round(load_s, 1), "size_gb": round(m["size"] / 1e9, 1),
                    "gpu_fraction": round(m["size_vram"] / m["size"], 3) if m["size"] else 0.0,
                    "context_length": m.get("context_length")}
    return {"load_s": round(load_s, 1), "size_gb": None, "gpu_fraction": None}


def screen(name: str, options: dict, scenarios) -> dict:
    rec = {"model": name, "options": options, "fit": gpu_fit(name, options), "interviews": []}
    client = make_client(name, options)
    for sid, sc in scenarios.items():
        t0 = time.perf_counter()
        try:
            turns = run_hybrid(sc, 0, client)
        except LLMError as e:
            rec["interviews"].append({"scenario": sid, "error": str(e)})
            print(f"  {sid:26} ÉCHEC {e}", flush=True)
            continue
        rec["interviews"].append({"scenario": sid, "turns": turns})
        print(f"  {sid:26} {time.perf_counter() - t0:6.1f}s", flush=True)
    unload(name)
    rec["summary"] = summarize(rec)
    return rec


def summarize(rec: dict) -> dict:
    turns = [t for i in rec["interviews"] if "turns" in i for t in i["turns"]]
    if not turns:
        return {"turns": 0, "failed_interviews": len(rec["interviews"])}
    llm = [t for t in turns if not t["fallback"]]  # replies actually written by the model
    reasons = Counter(r.split(":")[0] for t in turns for attempt in t["rejected"] for r in attempt)
    words = [w.strip(".,!?…«»\"'") for t in llm for w in t["child"].lower().split()]
    return {
        "turns": len(turns),
        "failed_interviews": sum("error" in i for i in rec["interviews"]),
        "fallback_rate": round(sum(t["fallback"] for t in turns) / len(turns), 3),
        "first_try_ok": round(sum(not t["rejected"] for t in turns) / len(turns), 3),
        "rejections": dict(reasons.most_common()),
        "latency_s": round(st.mean(t["latency_s"] for t in turns), 2),
        "words_per_reply": round(st.mean(len(t["child"].split()) for t in llm), 1) if llm else None,
        "role_breaks": sum(bool(ROLE_BREAK.search(t["child"])) for t in llm),
        "english_words": sum(w in ENGLISH for w in words),
    }


def report(records: list[dict], candidates: dict) -> str:
    rows = sorted(records, key=lambda r: (r["summary"].get("fallback_rate", 1), r["summary"].get("latency_s", 99)))
    out = ["# Tri des modèles candidats (voix de l'enfant)\n",
           "7 entretiens hybrides par modèle (un par scénario, graine 0), 23 tours scriptés. "
           "Repli = le filtre a rejeté deux mises en mots et le gabarit a répondu.\n",
           "| Modèle | Famille | Prio. | Sur GPU | Repli | OK du 1er coup | Motifs de rejet | Latence/tour | Mots/réponse "
           "| Hors rôle | Mots anglais |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s, f, c = r["summary"], r["fit"], candidates.get(r["model"], {})
        if not s.get("turns"):
            out.append(f"| `{r['model']}` | {c.get('family', '')} | {c.get('priority', '')} | — | échec | | | | | | |")
            continue
        gpu = f"{100 * f['gpu_fraction']:.0f} %" if f.get("gpu_fraction") is not None else "?"
        rej = ", ".join(f"{k} {v}" for k, v in s["rejections"].items()) or "—"
        out.append(f"| `{r['model']}` | {c.get('family', '')} | {c.get('priority', '')} | {gpu} | "
                   f"{100 * s['fallback_rate']:.1f} % | {100 * s['first_try_ok']:.0f} % | {rej} | {s['latency_s']:.1f} s | "
                   f"{s['words_per_reply']} | {s['role_breaks']} | {s['english_words']} |")
    out += ["", "Sur GPU < 100 % : une partie du modèle tourne sur le CPU (beaucoup plus lent). "
            "Motifs : leak = fait non autorisé, missing = fait autorisé absent, too_long = « je sais pas » qui brode, "
            "contradicts = contredit la décision du moteur, emoji, forbidden = lexique interdit.", ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(HERE / "candidates.yaml"))
    ap.add_argument("--priority", type=int, nargs="+", help="screen the candidates with these priorities")
    ap.add_argument("--models", nargs="+", help="explicit model names (override --priority)")
    ap.add_argument("--pull", action="store_true", help="download missing models first (large downloads)")
    ap.add_argument("--force", action="store_true", help="re-screen models already screened")
    args = ap.parse_args()
    candidates = {canonical(k): v for k, v in load_candidates(args.config).items()}
    if args.models:
        names = [canonical(m) for m in args.models]
    else:
        prio = set(args.priority or [1])
        names = [n for n, c in candidates.items() if c.get("priority") in prio]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "screening.jsonl"
    records = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
    done = {r["model"] for r in records}
    have = installed()
    scenarios = load_scenarios(ROOT / "scenarios")
    for name in names:
        if name in done and not args.force:
            print(f"{name}: déjà trié", flush=True)
            continue
        if name not in have:
            if not args.pull:
                print(f"{name}: absent (relancer avec --pull pour le télécharger)", flush=True)
                continue
            if not pull(name):
                print(f"{name}: téléchargement impossible", flush=True)
                continue
        print(f"{name}", flush=True)
        rec = screen(name, candidates.get(name, {}).get("options") or {}, scenarios)
        records = [r for r in records if r["model"] != name] + [rec]
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        print(f"  → {json.dumps(rec['summary'], ensure_ascii=False)}", flush=True)
    text = report(records, candidates)
    (OUT / "screening.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
