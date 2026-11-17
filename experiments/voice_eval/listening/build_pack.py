"""N1 — Build the blind listening pack (prepared, not launched).

    uv run python experiments/voice_eval/listening/build_pack.py

Writes listening/pack/clips/cXXX.wav (anonymous names), listening/pack/tasks.json (what the rating
page loads: no hidden truth) and listening/pack/design.json (for the analysis only):
- `clips`: what each clip IS (hidden from listeners: decided hesitation, cause, lie, voice…);
- `tasks`: what listeners are asked, per clip or per pair.
Blocks:
- gradient: 10 texts × hesitation 0 / 0.5 / 0.9 → rating 1–5 « cet enfant hésite » + naturalness + age;
- pairs: same text, two hesitation levels → which one hesitates more (2AFC);
- causes: corpus replies with comparable hesitation (0.5–0.7) dominated by memory, emotion or confusion;
- lie: 10 lies + 10 truths from controlled pairs (different facts) → « cet enfant ment-il ? »;
- references: child voice without any delivery, adult voice.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from lie_pairs import pairs
from sim import corpus

from nichd_sim.delivery import Delivery, HesitationCause, make_delivery, plan_speech
from nichd_sim.parameters import Parameters
from nichd_sim.realization import TemplateRealizer
from nichd_sim.scenario import AgeBand
from nichd_sim.voice import KokoroSpeaker, render_speech

PACK = HERE / "pack"
LEVELS = (0.0, 0.5, 0.9)


def main() -> None:
    rng = random.Random(2026)
    params = Parameters.load(AgeBand.B7_9)
    replies = corpus(range(2))
    long = [r for r in replies if len(r.result.response.split()) >= 8 and r.decision.lie is None]
    rng.shuffle(long)
    texts = list(dict.fromkeys(r.result.response for r in long))[:10]
    clips, tasks = [], []
    (PACK / "clips").mkdir(parents=True, exist_ok=True)
    with KokoroSpeaker() as child:
        adult = KokoroSpeaker(child=False, share_with=child)

        def add(text: str, delivery: Delivery | None, meta: dict, speaker=child) -> str:
            cid = f"c{len(clips):03d}"
            render_speech(plan_speech(text, delivery or Delivery(onset_ms=400)), speaker,
                          delivery).audio.write_wav(PACK / "clips" / f"{cid}.wav")
            clips.append({"id": cid, "text": text, "hesitation": delivery.hesitation if delivery else 0.0,
                          "loads": {str(k): v for k, v in (delivery.loads if delivery else {}).items()}, **meta})
            return cid

        gradient: dict[int, dict[float, str]] = {}
        for k, text in enumerate(texts):
            for level in LEVELS:
                loads = {HesitationCause.AFFECT: level / params["hesitation_weights"]["affect"]} if level else {}
                d = make_delivery(loads, params, random.Random(f"{k}:{level}"))
                gradient.setdefault(k, {})[level] = add(text, d, {"block": "gradient", "text_id": k, "level": level})
        for k, by_level in gradient.items():
            for a, b in ((0.0, 0.9), (0.5, 0.9), (0.0, 0.5)):
                tasks.append({"kind": "pair", "clips": [by_level[a], by_level[b]], "more_hesitant": by_level[b]})
        for cause in (HesitationCause.RETRIEVAL, HesitationCause.AFFECT, HesitationCause.CONFUSION):
            # comparable hesitation: the 6 replies of this dominant cause closest to 0.6
            pool = [r for r in replies if r.decision.delivery.dominant_cause == cause and r.result.response.strip()
                    and len(r.result.response.split()) >= 3]
            pool.sort(key=lambda r: abs(r.decision.delivery.hesitation - 0.6))
            for r in pool[:6]:
                add(r.result.response, r.decision.delivery, {"block": "causes", "cause": str(cause)})
        # Lie: SAME text (the true fact), rendered with the truthful delivery and with the lying delivery
        # of the same controlled pair — only the voice differs (the text would give an excuse away).
        ps = pairs(range(10))
        rng.shuffle(ps)
        per_text: dict[str, int] = {}
        n = 0
        for qtype, lie, truth in ps:
            text = TemplateRealizer().realize(truth, None, []).text
            if n >= 10 or per_text.get(text, 0) >= 2:
                continue
            per_text[text] = per_text.get(text, 0) + 1
            add(text, truth.delivery, {"block": "lie", "lie": False, "pair": n, "question": qtype})
            add(text, lie.delivery, {"block": "lie", "lie": True, "pair": n, "question": qtype,
                                     "lie_kind": str(lie.lie.kind)})
            n += 1
        for text in texts[:5]:
            add(text, None, {"block": "reference", "voice": "enfant sans diction"})
            add(text, None, {"block": "reference", "voice": "adulte"}, speaker=adult)
    for c in clips:
        if c["block"] != "pair":
            tasks.append({"kind": "rate", "clips": [c["id"]],
                          "questions": ["hesitation", "naturalness", "age"] + (["lie"] if c["block"] == "lie" else [])})
    design = {"version": 1, "clips": clips, "tasks": tasks,
              "questions": {
                  "hesitation": "Cet enfant hésite-t-il ? (1 = pas du tout, 5 = beaucoup)",
                  "naturalness": "Cette voix est-elle naturelle ? (1 = très artificielle, 5 = très naturelle)",
                  "age": "Quel âge donnez-vous à cet enfant ? (années)",
                  "lie": "Selon vous, cet enfant ment-il ? (oui / non)",
                  "pair": "Lequel des deux enfants hésite le plus ? (A / B)",
              }}
    (PACK / "design.json").write_text(json.dumps(design, ensure_ascii=False, indent=1), encoding="utf-8")
    # What the rating page loads: no hidden truth (hesitation, cause, lie, voice, text).
    public = {"version": 1, "questions": design["questions"],
              "tasks": [{k: v for k, v in task.items() if k != "more_hesitant"} for task in tasks]}
    (PACK / "tasks.json").write_text(json.dumps(public, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(clips)} extraits, {len(tasks)} tâches → {PACK}")


if __name__ == "__main__":
    main()
