"""Authoring checks for scenario sheets, beyond schema validation.

Errors make a scenario unusable (e.g. a unit the omission check can never
accept); warnings flag likely problems (anchors too common, overlapping units,
thin target event). Used by `nichd-sim check-scenario` and by the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from nichd_sim.output_filter import load_lexicon
from nichd_sim.parameters import Parameters
from nichd_sim.scenario import Category, Centrality, Scenario, ValidationStatus
from nichd_sim.text import contains, mentions, normalize

# Everyday words that make poor anchors: a child uses them about anything,
# so they trigger false leaks (and false "expressed" verdicts).
COMMON_WORDS = {
    "deja", "maison", "ecole", "pris", "prendre", "appele", "appelle", "car", "soir", "matin", "jour",
    "partie", "parti", "sortie", "sorti", "fois", "fait", "faire", "dit", "dire", "vu", "voir", "aller",
    "alle", "venu", "venir", "monsieur", "dame", "papa", "maman", "enfant", "copain", "copine",
    "la", "le", "les", "un", "une", "il", "elle", "et", "avec", "dans",
}
MIN_CENTRAL_UNITS = 5
EXPECTED_CATEGORIES = {Category.WHO, Category.WHAT, Category.WHERE, Category.WHEN}


class Level(StrEnum):
    ERROR = "erreur"
    WARNING = "avertissement"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    level: Level
    message: str
    unit: str | None = None

    def __str__(self) -> str:
        where = f" [{self.unit}]" if self.unit else ""
        return f"{self.level}{where} : {self.message}"


def check_scenario(scenario: Scenario) -> list[Finding]:
    out: list[Finding] = []
    lexicon = load_lexicon()
    units = [u for _, u in scenario.all_units()]

    for u in units:
        value = normalize(u.value)
        if not any(mentions(value, a) for a in u.anchors):
            out.append(Finding(Level.ERROR, "aucune ancre n'apparaît dans la valeur : le contrôle d'omission "
                                            "rejettera toujours la réponse", u.id))
        for term in lexicon:
            if contains(value, term):
                out.append(Finding(Level.ERROR, f"la valeur contient un terme du lexique interdit ({term!r})", u.id))
        for a in u.anchors:
            n = normalize(a)
            if n in COMMON_WORDS:
                out.append(Finding(Level.WARNING, f"ancre trop courante {a!r} : fausses fuites probables", u.id))

    # Anchors shared by two units: leaks and omissions become ambiguous.
    for i, u in enumerate(units):
        for v in units[i + 1 :]:
            for a in u.anchors:
                if any(normalize(a) == normalize(b) for b in v.anchors):
                    out.append(Finding(Level.WARNING, f"ancre {a!r} partagée avec {v.id}", u.id))

    target = [u for _, u in scenario.target_units()]
    central = sum(u.centrality == Centrality.CENTRAL for u in target)
    if central < MIN_CENTRAL_UNITS:
        out.append(Finding(Level.WARNING, f"{central} unité(s) centrale(s) dans l'événement cible (conseillé : "
                                          f"au moins {MIN_CENTRAL_UNITS})"))
    missing = EXPECTED_CATEGORIES - {u.category for u in target}
    if missing:
        out.append(Finding(Level.WARNING, f"catégories absentes de l'événement cible : {', '.join(sorted(missing))}"))
    if scenario.neutral_event is None:
        out.append(Finding(Level.WARNING, "pas d'événement neutre : la pratique narrative ne pourra pas être menée"))

    params = Parameters.load(scenario.child_profile.age_band, scenario.parameter_overrides)
    if scenario.child_profile.reluctance >= params["no_disclosure_reluctance"]:
        out.append(Finding(Level.WARNING, "réticence au-delà du plafond : l'enfant ne dévoilera jamais "
                                          "(sauf baisse par le soutien)"))
    if scenario.status == ValidationStatus.DRAFT:
        out.append(Finding(Level.INFO, "brouillon : en attente de validation par un formateur NICHD"))
    return out
