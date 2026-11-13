"""Output filter: forbidden lexicon + leak check against the scenario anchors."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from typing import Iterable

from nichd_sim.engine import Decision, SpeechAct
from nichd_sim.scenario import Scenario
from nichd_sim.text import contains as _contains
from nichd_sim.text import mentions as _mentions
from nichd_sim.text import normalize


def load_lexicon() -> list[str]:
    text = resources.files("nichd_sim.data").joinpath("forbidden_lexicon.txt").read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


@dataclass
class FilterVerdict:
    ok: bool
    forbidden_terms: list[str] = field(default_factory=list)
    leaked_units: list[str] = field(default_factory=list)
    missing_units: list[str] = field(default_factory=list)
    """Allowed units the response failed to express (would distort the metrics)."""
    empty: bool = False
    too_long: bool = False
    """A content-free act (don't know, deny, reluctant…) that runs on: likely invented content."""
    contradicts: bool = False
    """The wording flips the engine's decision (a "yes" for a refusal, a "no" for an acquiescence)."""


CONTENT_FREE_ACTS = {
    SpeechAct.DONT_KNOW, SpeechAct.DENY, SpeechAct.RELUCTANT,
    SpeechAct.ACKNOWLEDGE, SpeechAct.CONFUSION, SpeechAct.SILENCE,
}
MAX_CONTENT_FREE_WORDS = 10
_YES = {"oui", "ouais", "ouai", "exactement"}
_NO = {"non", "nan"}


class OutputFilter:
    def __init__(self, scenario: Scenario, lexicon: Iterable[str] | None = None):
        self.scenario = scenario
        self.lexicon = list(lexicon) if lexicon is not None else load_lexicon()

    def check(self, text: str, decision: Decision, known_unit_ids: Iterable[str] = ()) -> FilterVerdict:
        """`known_unit_ids`: units the child may legitimately mention (already said or contaminated)."""
        norm = normalize(text)
        forbidden = [t for t in self.lexicon if _contains(norm, t)]

        permitted_ids = {u.id for u in decision.allowed_units} | set(known_unit_ids)
        # Words of permitted facts are never a leak, even if they are also another unit's anchor.
        permitted_text = " ".join(
            [u.value for u in decision.allowed_units]
            + [u.value for _, u in self.scenario.all_units() if u.id in permitted_ids]
        )
        permitted_norm = normalize(permitted_text)
        leaked = []
        for _, unit in self.scenario.all_units():
            if unit.id in permitted_ids:
                continue
            for anchor in unit.anchors:
                if _mentions(norm, anchor) and not _mentions(permitted_norm, anchor):
                    leaked.append(unit.id)
                    break
        missing = []
        if decision.speech_act in (SpeechAct.ANSWER, SpeechAct.ACQUIESCE):
            for au in decision.allowed_units:
                unit = self.scenario.unit(au.id)
                anchors = unit.anchors if unit is not None else []
                if anchors and not any(_mentions(norm, a) for a in anchors):
                    missing.append(au.id)
        empty = not norm and decision.speech_act != SpeechAct.SILENCE
        too_long = decision.speech_act in CONTENT_FREE_ACTS and len(norm.split()) > MAX_CONTENT_FREE_WORDS
        words = set(norm.split())
        contradicts = (decision.speech_act == SpeechAct.DENY and bool(words & _YES)) or (
            decision.speech_act == SpeechAct.ACQUIESCE and bool(words & _NO) and not words & _YES
        )
        return FilterVerdict(
            ok=not forbidden and not leaked and not missing and not empty and not too_long and not contradicts,
            contradicts=contradicts,
            empty=empty,
            too_long=too_long,
            forbidden_terms=forbidden,
            leaked_units=leaked,
            missing_units=missing,
        )
