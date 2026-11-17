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
    latest = {}  # one listening session (same seed) saved several times: keep its last save
    for f in sorted((HERE / "ratings").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        if data.get("version") != design.get("version", "v2-1"):
            continue  # ratings of another listening pack
        key = data.get("seed", f.name)
        if key not in latest or data.get("saved_at", "") >= latest[key][1].get("saved_at", ""):
            latest[key] = (f, data)
    files = [f for f, _ in latest.values()]
    per = collections.defaultdict(lambda: {"naturel": [], "fluidite": [], "age": collections.Counter(), "picks": 0})
    groups = 0
    by_reply = collections.defaultdict(dict)
    for f, data in latest.values():
        for clip, r in data.get("ratings", {}).items():
            if clip not in clip_variant:
                continue
            v = per[clip_variant[clip]]
            for k in ("naturel", "fluidite"):
                if r.get(k):
                    v[k].append(r[k])
            if r.get("naturel"):
                by_reply[design["clips"][clip]["reply"]][clip_variant[clip]] = (r.get("naturel"), r.get("fluidite"))
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
    order = [v for _, v, _ in sorted(rows, reverse=True)]
    replies = sorted(by_reply)
    lines += ["", "Détail par réponse (naturel / fluidité) :", "",
              "| Variante | " + " | ".join(replies) + " |", "|---|" + "---|" * len(replies)]
    for variant in order:
        cells = [("{}/{}".format(*by_reply[g][variant]) if variant in by_reply[g] else "—") for g in replies]
        lines.append(f"| {variant} | " + " | ".join(cells) + " |")
    text = "\n".join(lines)
    (HERE / f"results_{design.get('version', 'v2-1')}.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
