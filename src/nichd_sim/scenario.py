"""Scenario sheet: child profile and ground truth, loaded and validated from YAML."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Iterator

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class ScenarioError(ValueError):
    """Raised when a scenario sheet is missing or malformed."""


class Category(StrEnum):
    WHO = "who"
    WHAT = "what"
    WHERE = "where"
    WHEN = "when"
    FREQUENCY = "frequency"


class Centrality(StrEnum):
    CENTRAL = "central"
    PERIPHERAL = "peripheral"


class SegmentId(StrEnum):
    BEFORE = "before"
    DURING = "during"
    AFTER = "after"


SEGMENT_ORDER = [SegmentId.BEFORE, SegmentId.DURING, SegmentId.AFTER]


class AgeBand(StrEnum):
    B4_6 = "4_6"
    B7_9 = "7_9"
    B10_12 = "10_12"

    @classmethod
    def from_age(cls, age: int) -> AgeBand:
        if age <= 6:
            return cls.B4_6
        if age <= 9:
            return cls.B7_9
        return cls.B10_12


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InfoUnit(_Strict):
    id: str = Field(min_length=1)
    category: Category
    centrality: Centrality
    value: str = Field(min_length=1, description="Le fait, formulé du point de vue de l'enfant.")
    anchors: list[str] = Field(min_length=1, description="Mots d'ancrage (indices, contrôle de fuite).")

    @field_validator("anchors")
    @classmethod
    def _non_blank_anchors(cls, v: list[str]) -> list[str]:
        if any(not a.strip() for a in v):
            raise ValueError("les ancres ne peuvent pas être vides")
        return v


class Segment(_Strict):
    id: SegmentId
    units: list[InfoUnit] = Field(min_length=1)


class ChildProfile(_Strict):
    name: str = Field(min_length=1)
    age: int = Field(ge=4, le=12)
    reluctance: float = Field(ge=0, le=1)
    verbal_skills: float = Field(ge=0, le=1)
    suggestibility: float = Field(ge=0, le=1)

    @property
    def age_band(self) -> AgeBand:
        return AgeBand.from_age(self.age)


class Event(_Strict):
    """A set of chronological segments (target event or neutral event)."""

    segments: list[Segment] = Field(min_length=1)

    @field_validator("segments")
    @classmethod
    def _chronological(cls, v: list[Segment]) -> list[Segment]:
        ids = [s.id for s in v]
        if len(set(ids)) != len(ids):
            raise ValueError("chaque segment (before/during/after) ne peut apparaître qu'une fois")
        if ids != sorted(ids, key=SEGMENT_ORDER.index):
            raise ValueError("les segments doivent être dans l'ordre chronologique before → during → after")
        return v

    def units(self) -> Iterator[tuple[SegmentId, InfoUnit]]:
        for seg in self.segments:
            for unit in seg.units:
                yield seg.id, unit


class EventKind(StrEnum):
    TARGET = "target"
    NEUTRAL = "neutral"


class Scenario(_Strict):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    intake_context: str = Field(min_length=1, description="Contexte de saisine montré à l'apprenant (sans les faits).")
    child_profile: ChildProfile
    target_event: Event
    neutral_event: Event | None = Field(
        default=None, description="Événement neutre récent, pour la pratique narrative."
    )
    parameter_overrides: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique_unit_ids(self) -> Scenario:
        seen: set[str] = set()
        for _, unit in self.all_units():
            if unit.id in seen:
                raise ValueError(f"identifiant d'unité dupliqué : {unit.id!r}")
            seen.add(unit.id)
        return self

    def event(self, kind: EventKind) -> Event | None:
        return self.target_event if kind == EventKind.TARGET else self.neutral_event

    def target_units(self) -> Iterator[tuple[SegmentId, InfoUnit]]:
        yield from self.target_event.units()

    def neutral_units(self) -> Iterator[tuple[SegmentId, InfoUnit]]:
        if self.neutral_event is not None:
            yield from self.neutral_event.units()

    def all_units(self) -> Iterator[tuple[SegmentId, InfoUnit]]:
        """Units of both events (target first)."""
        yield from self.target_units()
        yield from self.neutral_units()

    def unit(self, unit_id: str) -> InfoUnit | None:
        return next((u for _, u in self.all_units() if u.id == unit_id), None)

    def locate(self, unit_id: str) -> tuple[EventKind, SegmentId] | None:
        for kind in EventKind:
            event = self.event(kind)
            if event is None:
                continue
            for seg, u in event.units():
                if u.id == unit_id:
                    return kind, seg
        return None

    def segment_of(self, unit_id: str) -> SegmentId | None:
        loc = self.locate(unit_id)
        return loc[1] if loc else None

    def is_target_unit(self, unit_id: str | None) -> bool:
        loc = self.locate(unit_id) if unit_id else None
        return loc is not None and loc[0] == EventKind.TARGET


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a scenario sheet. Raises ScenarioError with a readable message."""
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ScenarioError(f"Scénario introuvable : {path}") from e
    except yaml.YAMLError as e:
        raise ScenarioError(f"Scénario {path.name} : YAML invalide ({e})") from e
    if not isinstance(raw, dict):
        raise ScenarioError(f"Scénario {path.name} : le document doit être un objet YAML")
    try:
        return Scenario.model_validate(raw)
    except ValidationError as e:
        lines = [f"Scénario {path.name} invalide :"]
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "(racine)"
            lines.append(f"  - {loc} : {err['msg']}")
        raise ScenarioError("\n".join(lines)) from e
