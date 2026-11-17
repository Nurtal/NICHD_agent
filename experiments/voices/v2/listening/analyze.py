"""Aggregate the blind listening ratings (ratings/*.json) with the hidden design (design.json).

    python experiments/voices/v2/listening/analyze.py
"""

import collections
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).parent


def main() -> None:
    design = json.loads((HERE / "design.json").read_text(encoding="utf-8"))
    clip_variant = {c: d["variant"] for c, d in design["clips"].items()}
    files = sorted((HERE / "ratings").glob("*.json"))
    per = collections.defaultdict(lambda: {"naturel": [], "fluidite": [], "age": collections.Counter(), "picks": 0})
    groups = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for clip, r in data.get("ratings", {}).items():
            v = per[clip_variant[clip]]
            for k in ("naturel", "fluidite"):
                if r.get(k):
                    v[k].append(r[k])
            if r.get("age"):
                v["age"][r["age"]] += 1
        for clip in data.get("picks", {}).values():
            per[clip_variant[clip]]["picks"] += 1
            groups += 1
    rows = []
    for variant, v in per.items():
        rows.append((st.mean(v["naturel"]) if v["naturel"] else 0, variant, v))
    lines = [f"Écoutes : {len(files)} fichier(s), {groups} choix de préférée", "",
             "| Variante | Naturel | Fluidité | Âge le plus cité | Préférée | Notes |", "|---|---|---|---|---|---|"]
    for nat, variant, v in sorted(rows, reverse=True):
        flu = st.mean(v["fluidite"]) if v["fluidite"] else 0
        age = v["age"].most_common(1)[0][0] if v["age"] else "—"
        lines.append(f"| {variant} | {nat:.2f} | {flu:.2f} | {age} | {v['picks']} | {len(v['naturel'])} |")
    text = "\n".join(lines)
    (HERE / "results.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
