"""Realizer port: turns an engine Decision into a child utterance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from nichd_sim.engine import Decision, SpeechAct
from nichd_sim.llm import ChatClient
from nichd_sim.scenario import AgeBand, ChildProfile


@dataclass
class Realization:
    text: str
    prompt: str | None = None
    """Prompt sent to the LLM, if any (logged)."""
    meta: dict = field(default_factory=dict)


class Realizer(Protocol):
    def realize(
        self, decision: Decision, profile: ChildProfile, history: list[tuple[str, str]], attempt: int = 0
    ) -> Realization: ...


FALLBACK_RESPONSES: dict[SpeechAct, str] = {
    SpeechAct.ANSWER: "Euh… je sais plus trop.",
    SpeechAct.DONT_KNOW: "Je sais pas.",
    SpeechAct.ACQUIESCE: "Oui.",
    SpeechAct.DENY: "Non.",
    SpeechAct.CONFABULATE: "Euh… je crois que oui.",
    SpeechAct.ACKNOWLEDGE: "D'accord.",
    SpeechAct.CONFUSION: "Hein ? Je comprends pas.",
    SpeechAct.SILENCE: "…",
}


class TemplateRealizer:
    """LLM-free realizer: renders the decision readably. For dev, demo without GPU, and tests."""

    def realize(self, decision, profile, history, attempt=0) -> Realization:
        if decision.speech_act in (SpeechAct.ANSWER, SpeechAct.ACQUIESCE) and decision.allowed_units:
            facts = ". ".join(u.value[0].upper() + u.value[1:] for u in decision.allowed_units)
            prefix = "Oui. " if decision.speech_act == SpeechAct.ACQUIESCE else ""
            return Realization(text=f"{prefix}{facts}.")
        return Realization(text=FALLBACK_RESPONSES[decision.speech_act])


# -- LLM realizer -----------------------------------------------------------

REGISTERS: dict[AgeBand, str] = {
    AgeBand.B4_6: (
        "Tu parles comme un vrai enfant de {age} ans à l'oral : phrases très courtes (3 à 8 mots), "
        "vocabulaire simple, parfois « euh », « y avait », répétitions. Tu ne situes pas bien le temps "
        "(pas de dates ni d'heures précises). Jamais de vocabulaire d'adulte."
    ),
    AgeBand.B7_9: (
        "Tu parles comme un enfant de {age} ans à l'oral : phrases simples, vocabulaire courant, "
        "quelques hésitations, enchaînements avec « et après », « et puis »."
    ),
    AgeBand.B10_12: (
        "Tu parles comme un enfant de {age} ans à l'oral : phrases complètes mais naturelles, "
        "vocabulaire courant, parfois un peu gêné ou laconique."
    ),
}

ACT_INSTRUCTIONS: dict[SpeechAct, str] = {
    SpeechAct.ANSWER: "Réponds à l'adulte en racontant TOUTES ces choses ({n}), dans cet ordre, avec tes mots, et RIEN d'autre :",
    SpeechAct.ACQUIESCE: "Tu dis oui à ce que l'adulte propose, en reprenant simplement son idée, et RIEN d'autre :",
    SpeechAct.DONT_KNOW: "Tu dis que tu ne sais pas, que tu ne te souviens pas. N'ajoute aucun détail.",
    SpeechAct.DENY: "Tu dis non. N'ajoute aucun détail.",
    SpeechAct.CONFABULATE: (
        "Tu ne connais pas la réponse mais tu réponds quand même : invente une réponse très courte "
        "et banale à la question (quelques mots), sans parler de rien d'autre."
    ),
    SpeechAct.ACKNOWLEDGE: "Tu réponds brièvement (d'accord, oui, hmm), sans raconter quoi que ce soit.",
    SpeechAct.CONFUSION: "Tu ne comprends pas ce que dit l'adulte et tu le dis simplement. N'ajoute aucun détail.",
    SpeechAct.SILENCE: "Tu ne dis presque rien (« … », « hmm »).",
}

RULES = (
    "Règles absolues : ne mentionne aucun fait, personne, lieu, objet ou émotion qui ne figure pas dans la liste. "
    "N'invente rien. Garde les mots importants de chaque fait. Pas de description physique ou violente détaillée. Une seule réplique orale, sans "
    "guillemets, sans retour à la ligne, sans didascalie ni astérisque."
)


def build_system_prompt(decision: Decision, profile: ChildProfile) -> str:
    lines = [
        f"Tu es {profile.name}, {profile.age} ans. Un adulte te pose des questions sur quelque chose que tu as vécu.",
        REGISTERS[profile.age_band].format(age=profile.age),
        ACT_INSTRUCTIONS[decision.speech_act].format(n=len(decision.allowed_units)),
    ]
    if decision.speech_act in (SpeechAct.ANSWER, SpeechAct.ACQUIESCE):
        lines += [f"{i}. {u.value}" for i, u in enumerate(decision.allowed_units, 1)]
        if len(decision.allowed_units) > 1:
            lines.append(f"Ta réponse doit contenir les {len(decision.allowed_units)} choses, aucune ne doit manquer.")
    lines.append(RULES)
    return "\n".join(lines)


class LLMRealizer:
    """Realizes decisions with a local LLM. Sees only the decision, the profile and a short history."""

    def __init__(self, client: ChatClient, *, seed: int = 0, temperature: float = 0.7, history_turns: int = 3):
        self.client = client
        self.seed = seed
        self.temperature = temperature
        self.history_turns = history_turns

    def realize(self, decision, profile, history, attempt=0) -> Realization:
        system = build_system_prompt(decision, profile)
        messages = [{"role": "system", "content": system}]
        recent = history[-2 * self.history_turns :]
        for speaker, text in recent:
            messages.append({"role": "user" if speaker == "interviewer" else "assistant", "content": text})
        # The current interviewer utterance is the last history entry when called by Session.
        seed = self.seed * 1000 + len(history) * 10 + attempt
        result = self.client.chat(messages, temperature=self.temperature, seed=seed, think=False)
        text = " ".join(result.content.split())
        return Realization(text=text, prompt=_render(messages), meta=result.meta)


def _render(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
