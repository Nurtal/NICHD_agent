"""N3, stage 2 — What transcription costs the classifier: κ on the original text vs on transcripts.

Same classifier and settings as in production (LLM, default reasoning); identical transcripts are
classified once. Slow (~13 s per utterance): run in the background.

    uv run python experiments/voice_eval/n3_classifier.py [--conditions moyen:None,moyen:10]
"""

from __future__ import annotations

import argparse
import json

from checks import RESULTS, Check, save

from nichd_sim.classifiers.llm import DEFAULT_CLASSIFIER_THINK, LLMClassifier
from nichd_sim.evaluation import evaluate, load_scenarios, load_testset
from nichd_sim.llm import DEFAULT_MODEL, OllamaClient

DEFAULT_CONDITIONS = ["grave-lent:None", "moyen:None", "aigu-rapide:None", "moyen:20", "moyen:10", "moyen:5"]


class Cached:
    def __init__(self, inner):
        self.inner, self.cache = inner, {}

    def classify(self, utterance, ctx):
        key = (utterance, tuple(ctx.revealed_unit_ids), ctx.scenario.id)
        if key not in self.cache:
            self.cache[key] = self.inner.classify(utterance, ctx)
        return self.cache[key]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    args = ap.parse_args()
    items = load_testset()
    transcripts = json.loads((RESULTS / "n3_transcripts.json").read_text(encoding="utf-8"))
    scenarios = load_scenarios()
    think = False if DEFAULT_CLASSIFIER_THINK in ("off", "false", "0") else DEFAULT_CLASSIFIER_THINK
    inner = LLMClassifier(OllamaClient(DEFAULT_MODEL), think=think)
    clf = Cached(inner)
    version = getattr(inner, "skill_version", "?")
    progress = lambda k, n, r: print(f"  {k}/{n} {r.id} {r.pred['type']}", flush=True) if k % 20 == 0 else None
    print("texte d'origine", flush=True)
    base = evaluate(clf, items, scenarios, model=DEFAULT_MODEL, skill_version=version, progress=progress)
    out = {"text": {"kappa": base.kappa, "type_acc": base.type_accuracy, "target_acc": base.target_accuracy}}
    checks = [Check("N3", "κ du classifieur sur le texte d'origine (référence)", base.kappa, "rapporté", None,
                    f"{DEFAULT_MODEL}, réflexion {DEFAULT_CLASSIFIER_THINK}")]
    for cond in args.conditions.split(","):
        speaker, snr = cond.split(":")
        snr = None if snr == "None" else int(snr)
        heard = {r["id"]: r["transcript"] for r in transcripts if r["speaker"] == speaker and r["snr"] == snr}
        if not heard:
            continue
        print(f"{speaker} {snr}", flush=True)
        variant = [dict(i, utterance=heard[i["id"]]) for i in items if i["id"] in heard]
        rep = evaluate(clf, variant, scenarios, model=DEFAULT_MODEL, skill_version=version, progress=progress)
        delta = base.kappa - rep.kappa
        flipped = [{"id": a.id, "texte": a.utterance, "transcription": b.utterance, "attendu": a.gold["type"],
                    "sur_texte": a.pred["type"], "sur_transcription": b.pred["type"]}
                   for a, b in zip(base.items, rep.items) if a.type_ok and not b.type_ok]
        out[cond] = {"kappa": rep.kappa, "type_acc": rep.type_accuracy, "target_acc": rep.target_accuracy,
                     "flipped": flipped}
        label = f"« {speaker} »" + ("" if snr is None else f", {snr} dB")
        judged = snr is None or snr >= 10
        checks.append(Check("N3", f"Δκ texte → transcription, {label}", delta,
                            "≤ 0,05" if judged else "rapporté", delta <= 0.05 if judged else None,
                            f"κ = {rep.kappa:.3f} ; {len(flipped)} énoncé(s) basculé(s) en erreur ; synthétique"))
        save("n3_classifier", checks, {"conditions": out})  # incremental: survives an interruption


if __name__ == "__main__":
    main()
