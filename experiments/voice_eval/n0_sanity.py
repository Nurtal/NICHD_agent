"""Sanity check of the N0 measurements themselves (voice env, no model needed).

1. Perfect ground truth: replies rendered with ToneSpeaker (a hum, digital silences): the segmentation
   must find every planned silence with a near-zero error, and no unplanned pause.
2. Broken delivery: the same replies with their internal pauses removed must FAIL the pause recall.

    experiments/voice_eval/run_voice_env.sh n0_sanity.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from n0_fidelity import PLANNED_MS, overlap, silences

from nichd_sim.delivery import Delivery, plan_speech
from nichd_sim.voice import ToneSpeaker, render_speech

TEXTS = [
    "C'était à la maison, dans la cuisine, et j'avais renversé mon verre de jus d'orange.",
    "On est allés à la piscine avec la classe et après on a mangé des gâteaux dans le car.",
    "Le chien aboyait très fort et les lunettes du monsieur sont tombées par terre.",
]


def measure(break_pauses: bool) -> tuple[float, float, float]:
    rng = random.Random(0)
    sp = ToneSpeaker(sample_rate=16000)
    hits = n = 0
    errors, unplanned = [], 0
    for k in range(30):
        d = Delivery(onset_ms=rng.randint(300, 2500), pauses_ms=[rng.randint(400, 1400) for _ in range(2)],
                     fillers=rng.randint(0, 2))
        plan = plan_speech(TEXTS[k % 3], d)
        planned = [(s.start_ms, s.end_ms) for s in render_speech(plan, sp, d).timeline
                   if s.kind == "silence" and s.end_ms - s.start_ms >= PLANNED_MS]
        rendered_d = d.model_copy(update={"pauses_ms": [0, 0]}) if break_pauses else d
        audio = render_speech(plan_speech(TEXTS[k % 3], rendered_d), sp, rendered_d).audio
        y = np.array(audio.samples, dtype=np.float32)
        sil = silences(y, audio.sample_rate)
        for p in planned:
            n += 1
            best = max(sil, key=lambda m: overlap(m, p), default=None)
            if best and overlap(best, p) >= 0.5 * (p[1] - p[0]):
                hits += 1
                errors.append(abs((best[1] - best[0]) - (p[1] - p[0])))
        unplanned += sum(1 for m in sil if m[1] - m[0] >= PLANNED_MS
                         and all(overlap(m, p) < 0.5 * (m[1] - m[0]) for p in planned))
    return hits / n, (sum(errors) / len(errors) if errors else float("nan")), unplanned / 30


def main() -> None:
    rec, err, up = measure(break_pauses=False)
    print(f"vérité parfaite : rappel {rec:.2f}, erreur de durée {err:.0f} ms, pauses non planifiées {up:.2f}")
    assert rec == 1.0 and err <= 20 and up == 0, "la segmentation ne retrouve pas une vérité parfaite"
    rec_b, _, _ = measure(break_pauses=True)
    print(f"diction cassée (pauses supprimées) : rappel {rec_b:.2f}")
    assert rec_b < 0.95, "une diction cassée devrait faire échouer le rappel des silences"
    print("OK : les mesures N0 distinguent une diction correcte d'une diction cassée")


if __name__ == "__main__":
    main()
