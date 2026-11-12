"""Behavior parameters: per-age-band values, each with its literature source."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from nichd_sim.scenario import AgeBand


class ParameterError(ValueError):
    pass


class Parameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    source: str = Field(min_length=1, description="Référence bibliographique ou justification.")
    estimated: bool = Field(description="Vrai si la valeur est extrapolée plutôt que lue dans la source.")
    value: Any = None
    values: dict[AgeBand, Any] | None = None

    @model_validator(mode="after")
    def _one_of(self) -> Parameter:
        if (self.value is None) == (self.values is None):
            raise ValueError("un paramètre définit soit `value`, soit `values` par bande d'âge")
        if self.values is not None and set(self.values) != set(AgeBand):
            raise ValueError("`values` doit couvrir les trois bandes d'âge 4_6, 7_9, 10_12")
        return self

    def for_band(self, band: AgeBand) -> Any:
        return self.value if self.values is None else self.values[band]


class Parameters:
    """Default parameters merged with scenario overrides, resolved for one age band."""

    def __init__(self, table: Mapping[str, Parameter], band: AgeBand, overrides: Mapping[str, Any] | None = None):
        self.table = dict(table)
        self.band = band
        self.overrides = dict(overrides or {})
        unknown = set(self.overrides) - set(self.table)
        if unknown:
            raise ParameterError(f"surcharge de paramètre inconnu : {', '.join(sorted(unknown))}")

    @classmethod
    def load(cls, band: AgeBand, overrides: Mapping[str, Any] | None = None, path: str | Path | None = None) -> Parameters:
        if path is None:
            table = _default_table()
        else:
            table = _parse(Path(path).read_text(encoding="utf-8"))
        return cls(table, band, overrides)

    def __getitem__(self, name: str) -> Any:
        if name in self.overrides:
            ov = self.overrides[name]
            if isinstance(ov, Mapping):
                return ov.get(self.band.value, ov.get(self.band, self.table[name].for_band(self.band)))
            return ov
        try:
            return self.table[name].for_band(self.band)
        except KeyError as e:
            raise ParameterError(f"paramètre inconnu : {name}") from e

    def snapshot(self) -> dict[str, Any]:
        """Resolved values, for the session log."""
        return {name: self[name] for name in sorted(self.table)}


def _parse(text: str) -> dict[str, Parameter]:
    raw = yaml.safe_load(text) or {}
    return {name: Parameter.model_validate(spec) for name, spec in raw.items()}


@lru_cache(maxsize=1)
def _default_table() -> dict[str, Parameter]:
    return _parse(resources.files("nichd_sim.data").joinpath("parameters.yaml").read_text(encoding="utf-8"))
