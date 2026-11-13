"""Realizer port: turns an engine Decision into a child utterance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from nichd_sim.engine import Decision, SpeechAct
from nichd_sim.scenario import ChildProfile


@dataclass
class Realization:
    text: str
    prompt: str | None = None
    """Prompt sent to the LLM, if any (logged)."""
    meta: dict = field(default_factory=dict)


class Realizer(Protocol):
    def realize(self, decision: Decision, profile: ChildProfile, history: list[tuple[str, str]]) -> Realization: ...


FALLBACK_RESPONSES: dict[SpeechAct, str] = {
    SpeechAct.ANSWER: "Euh…",
    SpeechAct.DONT_KNOW: "Je sais pas.",
    SpeechAct.ACQUIESCE: "Oui.",
    SpeechAct.DENY: "Non.",
    SpeechAct.ACKNOWLEDGE: "D'accord.",
    SpeechAct.CONFUSION: "Hein ? Je comprends pas.",
    SpeechAct.SILENCE: "…",
}


class TemplateRealizer:
    """LLM-free realizer: renders the decision readably. For dev, demo without GPU, and tests."""

    def realize(self, decision: Decision, profile: ChildProfile, history: list[tuple[str, str]]) -> Realization:
        if decision.speech_act in (SpeechAct.ANSWER, SpeechAct.ACQUIESCE) and decision.allowed_units:
            facts = ". ".join(u.value[0].upper() + u.value[1:] for u in decision.allowed_units)
            prefix = "Oui. " if decision.speech_act == SpeechAct.ACQUIESCE else ""
            return Realization(text=f"{prefix}{facts}.")
        return Realization(text=FALLBACK_RESPONSES[decision.speech_act])
