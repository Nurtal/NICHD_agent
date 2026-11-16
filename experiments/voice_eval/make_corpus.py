"""N0/N1-auto corpus: simulated replies rendered with Kokoro, with their ground truth.

    uv run python experiments/voice_eval/make_corpus.py [--n 500]

Writes results/audio/ (not versioned) and results/corpus.json:
- `replies`: a stratified sample of simulated replies (all hesitation levels, volumes, fillers),
  each with its plan (planned silences and fillers), delivery, and the anchors of the units said;
- `rate` / `volume`: controlled renders (same texts at several rates / volumes);
- `determinism`: hashes of the same replies rendered twice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from sim import corpus

from nichd_sim.delivery import ChunkKind, Delivery, Volume, plan_speech
from nichd_sim.engine import SpeechAct
from nichd_sim.scenario import load_scenario
from nichd_sim.voice import KokoroSpeaker, render_speech

HERE = Path(__file__).parent
OUT = HERE / "results"
AUDIO = OUT / "audio"
ROOT = HERE.parents[1]

RATE_TEXTS = [
    "C'était à la maison, dans la cuisine, et j'avais renversé mon verre de jus d'orange.",
    "On est allés à la piscine avec la classe et j'ai fait le grand toboggan.",
    "Le chien de Monsieur Bertin aboyait très fort à côté du banc vert.",
    "Je suis allée dans ma chambre et après j'ai pleuré.",
    "Elle a mis le portefeuille dans son sac et la boulangère n'a rien vu.",
    "Ils m'ont demandé les dix euros de la cantine devant le collège.",
    "Mon petit frère Nolan pleurait et la télé était allumée.",
    "Papi a pris des photos avec son téléphone pendant le spectacle.",
]


def anchors_of(scenarios: dict, scenario_id: str, unit_id: str) -> list[str]:
    sc = scenarios[scenario_id.split("@")[0]]
    unit = sc.unit(unit_id) or sc.lie_unit(unit_id)
    return list(unit.anchors) if unit else []


def sample(replies, n: int, rng: random.Random):
    speaking = [r for r in replies if r.decision.speech_act != SpeechAct.SILENCE and r.result.response.strip()]
    # stratify on hesitation deciles, so that strong hesitations are not drowned by small talk
    bins: dict[int, list] = {}
    for r in speaking:
        bins.setdefault(min(9, int(r.decision.delivery.hesitation * 10)), []).append(r)
    per_bin = max(1, n // len(bins))
    out = []
    for b in sorted(bins):
        rng.shuffle(bins[b])
        out += bins[b][:per_bin]
    return out[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    rng = random.Random(0)
    scenarios = {load_scenario(p).id: load_scenario(p) for p in sorted((ROOT / "scenarios").glob("s0*.yaml"))}
    replies = sample(corpus(range(args.seeds)), args.n, rng)
    data = {"replies": [], "rate": [], "volume": [], "determinism": []}
    with KokoroSpeaker() as sp:
        for i, r in enumerate(replies):
            d = r.decision
            rendered = render_speech(r.result.speech_plan, sp, d.delivery)
            path = rendered.audio.write_wav(AUDIO / "replies" / f"r{i:04d}.wav")
            data["replies"].append({
                "id": f"r{i:04d}", "wav": str(path.relative_to(OUT)), "scenario": r.scenario, "style": r.style,
                "age_band": r.age_band, "speech_act": str(d.speech_act), "question_type": r.question_type,
                "text": r.result.response, "lie": d.lie.kind if d.lie else None,
                "delivery": d.delivery.model_dump(mode="json"),
                "plan": [c.model_dump(mode="json") for c in r.result.speech_plan],
                "timeline": [{"kind": str(s.kind), "start_ms": s.start_ms, "end_ms": s.end_ms, "text": s.text}
                             for s in rendered.timeline],
                "units": [{"id": u.id, "lie": u.lie, "contaminated": u.contaminated,
                           "anchors": [] if u.contaminated else anchors_of(scenarios, r.scenario, u.id)}
                          for u in d.allowed_units],
            })
            if i < 20:  # determinism: render again, compare bytes
                again = render_speech(r.result.speech_plan, sp, d.delivery).audio.samples.tobytes()
                data["determinism"].append(hashlib.sha256(rendered.audio.samples.tobytes()).hexdigest()
                                           == hashlib.sha256(again).hexdigest())
        for k, text in enumerate(RATE_TEXTS):
            for rate in (0.75, 0.85, 1.0):
                dl = Delivery(onset_ms=300, rate=rate)
                rr = render_speech(plan_speech(text, dl), sp, dl)
                p = rr.audio.write_wav(AUDIO / "rate" / f"t{k}_{rate}.wav")
                data["rate"].append({"text_id": k, "rate": rate, "wav": str(p.relative_to(OUT)),
                                     "speech_ms": sum(s.end_ms - s.start_ms for s in rr.timeline
                                                      if s.kind == ChunkKind.SPEECH)})
            for vol in Volume:
                dl = Delivery(onset_ms=300, volume=vol)
                rr = render_speech(plan_speech(text, dl), sp, dl)
                p = rr.audio.write_wav(AUDIO / "volume" / f"t{k}_{vol}.wav")
                data["volume"].append({"text_id": k, "volume": str(vol), "wav": str(p.relative_to(OUT))})
    (OUT / "corpus.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(data['replies'])} réponses, {len(data['rate'])} rendus de débit, {len(data['volume'])} de volume")


if __name__ == "__main__":
    main()
