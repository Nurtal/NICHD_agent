"""Sanity check of analyze.py: simulated listeners (never mixed with real ratings).

    uv run python experiments/voice_eval/listening/simulate_ratings.py ideal|random OUT_DIR

- ideal: hear the decided hesitation (with noise), cannot tell lies from voice, like the voice;
- random: answer at random. analyze.py must pass the first and fail the second.
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
kind, out = sys.argv[1], Path(sys.argv[2])
design = json.loads((HERE / "pack" / "design.json").read_text(encoding="utf-8"))
clips = {c["id"]: c for c in design["clips"]}
out.mkdir(parents=True, exist_ok=True)
for k in range(5):
    rng = random.Random(f"{kind}{k}")
    answers = []
    for i, t in enumerate(design["tasks"]):
        if t["kind"] == "pair":
            a, b = t["clips"]
            if kind == "ideal":
                ha, hb = (clips[c]["hesitation"] + rng.gauss(0, 0.1) for c in (a, b))
                choice = a if ha > hb else b
            else:
                choice = rng.choice([a, b])
            answers.append({"task": i, "clips": t["clips"], "pair": choice})
        else:
            c = clips[t["clips"][0]]
            h = c["hesitation"]
            ans = {"task": i, "clips": t["clips"],
                   "hesitation": str(max(1, min(5, round(1 + 4 * h + rng.gauss(0, 0.5))))) if kind == "ideal"
                   else str(rng.randint(1, 5)),
                   "naturalness": str(rng.choice([3, 4]) if kind == "ideal" else rng.randint(1, 5)),
                   "age": str(rng.randint(7, 10) if kind == "ideal" else rng.randint(3, 16))}
            if "lie" in t["questions"]:
                ans["lie"] = rng.choice(["oui", "non"])
            answers.append(ans)
    (out / f"ecoute_{kind}{k}.json").write_text(json.dumps({"listener": f"{kind}{k}", "answers": answers}))
