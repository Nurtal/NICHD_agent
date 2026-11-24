"""LLM classifier: NICHD typology via a local model guided by the versioned NICHD skill."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml
from pydantic import ValidationError

from nichd_sim.classification import OUT_OF_SCENARIO, Classification, ClassificationContext, QuestionType
from nichd_sim.llm import ChatClient, LLMError


@dataclass(frozen=True)
class Skill:
    version: str
    spec: str
    schema: dict
    examples: list[dict]
    example_catalog: list[dict]

    @classmethod
    def load(cls) -> Skill:
        root = resources.files("nichd_sim.skill")
        return cls(
            version=root.joinpath("VERSION").read_text(encoding="utf-8").strip(),
            spec=root.joinpath("spec.md").read_text(encoding="utf-8"),
            schema=json.loads(root.joinpath("schema.json").read_text(encoding="utf-8")),
            examples=[json.loads(ln) for ln in root.joinpath("examples.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()],
            example_catalog=yaml.safe_load(root.joinpath("example_catalog.yaml").read_text(encoding="utf-8")),
        )


def _catalog_lines(units: list[dict]) -> str:
    return "\n".join(f"- {u['id']} ({u['category']}) : {u['value']}" for u in units)


def build_system_prompt(skill: Skill) -> str:
    examples = []
    for ex in skill.examples:
        said = ", ".join(ex["already_said"]) or "rien"
        examples.append(
            f"Déjà dit par l'enfant : {said}\nÉnoncé : {ex['utterance']}\n→ {json.dumps(ex['label'], ensure_ascii=False)}"
        )
    return (
        skill.spec
        + "\n\n## Exemples\n\nCatalogue utilisé par les exemples (fictif) :\n"
        + _catalog_lines(skill.example_catalog)
        + "\n\n"
        + "\n\n".join(examples)
    )


def build_user_prompt(utterance: str, context: ClassificationContext, history_turns: int) -> str:
    units = [
        {"id": u.id, "category": u.category.value, "value": u.value} for _, u in context.scenario.all_units()
    ]
    said = ", ".join(context.revealed_unit_ids) or "rien"
    recent = context.history[-2 * history_turns :]
    hist = "\n".join(f"{'Interviewer' if s == 'interviewer' else 'Enfant'} : {t}" for s, t in recent) or "(début)"
    return (
        "Catalogue des unités d'information de cet entretien :\n"
        f"{_catalog_lines(units)}\n\n"
        f"Historique récent :\n{hist}\n\n"
        f"Déjà dit par l'enfant : {said}\n"
        f"Énoncé à coder : {utterance}"
    )


CASCADE = "cascade"
DEFAULT_CLASSIFIER_THINK = CASCADE
"""Thinking level of the classifier ("off", "low", "medium", "high", or "cascade"): precision vs latency.
"cascade" answers fast without thinking and thinks again only where that first answer is risky. On the 133 test
utterances it is as accurate as thinking on every turn (κ 0.956 vs 0.947 for "medium") with a median of 3.6 s instead
of 15 s (docs/evaluations/latence.md)."""

CASCADE_THINK = "low"
"""Thinking level of the second pass ("low" measured better than "medium" there, and is faster)."""

ESCALATE_TYPES: frozenset[QuestionType] = frozenset({
    QuestionType.SUGGESTIVE, QuestionType.OPTION_POSING, QuestionType.DIRECTIVE, QuestionType.COMPOUND,
    QuestionType.OTHER,
})
"""Fast answers checked again with thinking: the closed and leading types, which cost most when wrong and on which the
fast pass errs (« tu sais… ? » read as a directive, wrong target), and "other". Out-of-scenario targets and invalid
outputs are checked too. Invitations, ground rules, support and facilitators keep the fast answer."""


def escalation_reason(c: Classification) -> str | None:
    """Why the fast answer of the cascade must be checked with thinking, or None to keep it."""
    if c.meta.get("error"):
        return "error"
    if c.type in ESCALATE_TYPES:
        return f"type:{c.type.value}"
    if c.target == OUT_OF_SCENARIO:
        return "out_of_scenario"
    return None


class LLMClassifier:
    def __init__(
        self, client: ChatClient, *, skill: Skill | None = None, think: bool | str = DEFAULT_CLASSIFIER_THINK,
        history_turns: int = 3,
    ):
        self.client = client
        self.skill = skill or Skill.load()
        self.think = think
        self.history_turns = history_turns
        self._system = build_system_prompt(self.skill)

    @property
    def skill_version(self) -> str:
        return self.skill.version

    def warm_up(self) -> None:
        """Load the model and read the system prompt once, before the first turn (a live session's start)."""
        try:
            self.client.chat([{"role": "system", "content": self._system}, {"role": "user", "content": "ok"}],
                             temperature=0, seed=0, think=False)
        except LLMError:
            pass  # the first turn will report it

    def classify(self, utterance: str, context: ClassificationContext) -> Classification:
        messages = [
            {"role": "system", "content": self._system},
            {"role": "user", "content": build_user_prompt(utterance, context, self.history_turns)},
        ]
        if self.think != CASCADE:
            return self._ask(messages, context, self.think)
        fast = self._ask(messages, context, False)
        reason = escalation_reason(fast)
        if reason is None:
            fast.meta["cascade"] = "fast"
            return fast
        checked = self._ask(messages, context, CASCADE_THINK)
        checked.meta.update(cascade="escalated", escalation=reason,
                            fast={"type": fast.type.value, "target": fast.target,
                                  "latency_s": fast.meta.get("latency_s")})
        return checked

    def _ask(self, messages: list[dict], context: ClassificationContext, think: bool | str) -> Classification:
        try:
            result = self.client.chat(messages, temperature=0, seed=0, think=think, format=self.skill.schema)
        except LLMError as e:
            return _fallback(f"llm_error: {e}", {})
        meta = dict(result.meta)
        try:
            raw = json.loads(result.content)
            return _to_classification(raw, context, meta)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as e:
            meta["raw"] = result.content
            return _fallback(f"invalid_output: {e.__class__.__name__}", meta)


def _to_classification(raw: dict[str, Any], context: ClassificationContext, meta: dict) -> Classification:
    target = raw.get("target")
    if target is not None and target != OUT_OF_SCENARIO and context.scenario.unit(target) is None:
        meta["unknown_target"] = target
        target = OUT_OF_SCENARIO
    qtype = QuestionType(raw["type"])
    if qtype not in _TARGETED and qtype != QuestionType.COMPOUND:
        target = None
    inner = raw.get("inner_type")
    phase = raw.get("phase_hint")
    return Classification(
        type=qtype,
        target=target,
        suggested_proposition=raw.get("suggested_proposition") or None,
        options=raw.get("options") or None,
        inner_type=QuestionType(inner) if inner and qtype == QuestionType.COMPOUND else None,
        phase_hints=[phase] if phase else [],
        segment=raw.get("segment") or None,
        knowledge_question=bool(raw.get("knowledge_question")),
        ground_rule_kind=(raw.get("ground_rule_kind") or None) if qtype == QuestionType.GROUND_RULE else None,
        practice_kind=raw.get("practice_kind") or None,
        causal=bool(raw.get("causal")),
        meta=meta,
    )


_TARGETED = {
    QuestionType.CUED_INVITATION,
    QuestionType.DIRECTIVE,
    QuestionType.OPTION_POSING,
    QuestionType.SUGGESTIVE,
}


def _fallback(error: str, meta: dict) -> Classification:
    return Classification(type=QuestionType.OTHER, meta={**meta, "error": error})
