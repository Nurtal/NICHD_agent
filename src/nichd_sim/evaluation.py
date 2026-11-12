"""Classifier evaluation against the skill's held-out test set."""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from nichd_sim.classification import ClassificationContext, Classifier
from nichd_sim.scenario import Scenario, load_scenario

KAPPA_TARGET = 0.70


def load_testset() -> list[dict]:
    text = resources.files("nichd_sim.skill").joinpath("testset.jsonl").read_text(encoding="utf-8")
    return [json.loads(ln) for ln in text.splitlines() if ln.strip()]


def cohen_kappa(gold: list[str], pred: list[str]) -> float:
    if not gold:
        return 0.0
    n = len(gold)
    observed = sum(g == p for g, p in zip(gold, pred)) / n
    cg, cp = Counter(gold), Counter(pred)
    expected = sum(cg[k] * cp[k] for k in set(cg) | set(cp)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


@dataclass
class ItemResult:
    id: str
    utterance: str
    gold: dict
    pred: dict
    ambiguous: bool
    latency_s: float

    @property
    def type_ok(self) -> bool:
        return self.gold["type"] == self.pred["type"]

    @property
    def target_ok(self) -> bool:
        return self.gold["target"] == self.pred["target"]


@dataclass
class EvalReport:
    model: str
    skill_version: str
    items: list[ItemResult] = field(default_factory=list)

    @property
    def kappa(self) -> float:
        return cohen_kappa([i.gold["type"] for i in self.items], [i.pred["type"] for i in self.items])

    @property
    def type_accuracy(self) -> float:
        return _mean(i.type_ok for i in self.items)

    @property
    def target_accuracy(self) -> float:
        """Over items whose gold label has a target."""
        return _mean(i.target_ok for i in self.items if i.gold["target"] is not None)

    @property
    def phase_accuracy(self) -> float:
        return _mean(i.gold["phase_hint"] == i.pred["phase_hint"] for i in self.items)

    def confusion(self) -> dict[tuple[str, str], int]:
        return Counter((i.gold["type"], i.pred["type"]) for i in self.items if not i.type_ok)

    def to_markdown(self) -> str:
        n = len(self.items)
        amb = [i for i in self.items if i.ambiguous]
        clear = [i for i in self.items if not i.ambiguous]
        lat = sorted(i.latency_s for i in self.items)
        verdict = "atteint" if self.kappa >= KAPPA_TARGET else "NON atteint"
        lines = [
            "# Évaluation du classifieur NICHD",
            "",
            f"- Modèle : `{self.model}` — skill v{self.skill_version} — {n} énoncés du jeu de test",
            f"- **Kappa de Cohen (type)** : **{self.kappa:.3f}** (objectif v1 ≥ {KAPPA_TARGET} : {verdict})",
            f"- Exactitude du type : {self.type_accuracy:.1%} "
            f"(non ambigus : {_mean(i.type_ok for i in clear):.1%}, ambigus : {_mean(i.type_ok for i in amb):.1%})",
            f"- Exactitude de la cible : {self.target_accuracy:.1%}",
            f"- Exactitude de l'indice de phase : {self.phase_accuracy:.1%}",
            f"- Latence : médiane {lat[n // 2]:.2f} s, max {lat[-1]:.2f} s" if lat else "",
            "",
            "## Confusions de type (attendu → prédit)",
            "",
        ]
        conf = self.confusion()
        lines += [f"- {g} → {p} : {k}" for (g, p), k in conf.most_common()] or ["- aucune"]
        lines += ["", "## Erreurs", "", "| id | énoncé | attendu | prédit |", "|---|---|---|---|"]
        for i in self.items:
            if i.type_ok and (i.gold["target"] is None or i.target_ok):
                continue
            g = f"{i.gold['type']} / {i.gold['target']}"
            p = f"{i.pred['type']} / {i.pred['target']}"
            amb_mark = " *(ambigu)*" if i.ambiguous else ""
            lines.append(f"| {i.id} | {i.utterance}{amb_mark} | {g} | {p} |")
        return "\n".join(lines) + "\n"


def evaluate(classifier: Classifier, items: list[dict], scenarios: dict[str, Scenario], *, model: str, skill_version: str, progress=None) -> EvalReport:
    report = EvalReport(model=model, skill_version=skill_version)
    for k, item in enumerate(items, 1):
        ctx = ClassificationContext(scenario=scenarios[item["scenario"]], revealed_unit_ids=list(item["already_said"]))
        t0 = time.perf_counter()
        c = classifier.classify(item["utterance"], ctx)
        elapsed = time.perf_counter() - t0
        pred = {
            "type": c.type.value,
            "target": c.target,
            "inner_type": c.inner_type.value if c.inner_type else None,
            "phase_hint": c.phase_hints[0] if c.phase_hints else None,
        }
        report.items.append(
            ItemResult(id=item["id"], utterance=item["utterance"], gold=item["label"], pred=pred,
                       ambiguous=item.get("ambiguous", False), latency_s=elapsed)
        )
        if progress:
            progress(k, len(items), report.items[-1])
    return report


def load_scenarios(directory: str | Path = "scenarios") -> dict[str, Scenario]:
    out = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        sc = load_scenario(path)
        out[sc.id] = sc
    return out


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
