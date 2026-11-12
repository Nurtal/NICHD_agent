"""Output filter: forbidden lexicon + leak check against the scenario anchors."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from importlib import resources
from typing import Iterable

from nichd_sim.engine import Decision, SpeechAct
from nichd_sim.scenario import Scenario


def normalize(text: str) -> str:
    """Lowercase, strip accents, unify apostrophes; keep word boundaries."""
    text = unicodedata.normalize("NFKD", text.replace("’", "'").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _contains(haystack_norm: str, needle: str) -> bool:
    """Whole-word match of a normalized phrase; `needle*` matches as a word prefix."""
    prefix = needle.endswith("*")
    n = normalize(needle.rstrip("*"))
    if not n:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(n) + (r"" if prefix else r"(?![a-z0-9])")
    return re.search(pattern, haystack_norm) is not None


def load_lexicon() -> list[str]:
    text = resources.files("nichd_sim.data").joinpath("forbidden_lexicon.txt").read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]


def _mentions(haystack_norm: str, anchor: str) -> bool:
    """Lenient match used for omission: single words match on a stem (inflections)."""
    n = normalize(anchor)
    if " " in n or len(n) <= 4:
        return _contains(haystack_norm, anchor)
    stem = n[: max(4, len(n) - 3)]
    return re.search(r"(?<![a-z0-9])" + re.escape(stem), haystack_norm) is not None


@dataclass
class FilterVerdict:
    ok: bool
    forbidden_terms: list[str] = field(default_factory=list)
    leaked_units: list[str] = field(default_factory=list)
    missing_units: list[str] = field(default_factory=list)
    """Allowed units the response failed to express (would distort the metrics)."""


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
        return FilterVerdict(
            ok=not forbidden and not leaked and not missing,
            forbidden_terms=forbidden,
            leaked_units=leaked,
            missing_units=missing,
        )
