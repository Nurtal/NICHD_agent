"""The rule catalogue: the parameters of the registry grouped into the child's behaviour rules, each with
its literature references, and the per-session configuration of those rules (switched off, adjusted),
which named presets store (model control panel)."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nichd_sim.parameters import Parameter, Parameters, _default_table
from nichd_sim.scenario import AgeBand

Evidence = Literal["tendance publiée", "choix de modélisation"]


class RuleError(ValueError):
    pass


class Reference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cite: str = Field(min_length=1)
    doi: str | None = None

    @property
    def url(self) -> str | None:
        return f"https://doi.org/{self.doi}" if self.doi else None


class ParamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    """What the slider is called in the panel."""
    primary: bool = False
    """Shown without unfolding the rule's advanced settings."""
    range: tuple[float, float, float] | None = None
    """Slider [min, max, step], for every key of a dict parameter or both ends of a pair. None: shown
    but not adjustable (booleans and labels have their own control)."""


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = ""
    title: str = Field(min_length=1)
    family: str
    summary: str = Field(min_length=1)
    evidence: Evidence
    toggle: bool = True
    """False: a base mechanism, adjustable but never switched off."""
    params: dict[str, ParamSpec] = Field(min_length=1)
    when_off: dict[str, Any] = {}
    """Values that switch the rule off; for the other parameters, their neutral value, if any."""
    refs: list[str] = []


class Catalogue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    families: dict[str, str]
    rules: dict[str, Rule]
    references: dict[str, Reference] = {}

    @model_validator(mode="after")
    def _ids(self) -> Catalogue:
        for rid, rule in self.rules.items():
            rule.id = rid
        return self

    def by_family(self) -> dict[str, list[Rule]]:
        out: dict[str, list[Rule]] = {f: [] for f in self.families}
        for rule in self.rules.values():
            out[rule.family].append(rule)
        return out

    def rule_of(self, param: str) -> Rule:
        for rule in self.rules.values():
            if param in rule.params:
                return rule
        raise RuleError(f"aucune règle ne porte le paramètre {param!r}")

    def off_values(self, rule_id: str, table: Mapping[str, Parameter]) -> dict[str, Any]:
        """The values that switch a rule off: explicit `when_off`, else the parameter's neutral value. A
        partial dict only replaces its keys (see `switch_off`)."""
        rule = self.rules[rule_id]
        out = {name: table[name].neutral for name in rule.params if table[name].has_neutral}
        out.update(rule.when_off)
        return out

    def validate_against(self, table: Mapping[str, Parameter]) -> None:
        """Every parameter of the registry in exactly one rule; every reference and family known;
        every switchable rule has something to switch off."""
        problems: list[str] = []
        seen: dict[str, str] = {}
        for rid, rule in self.rules.items():
            if rule.family not in self.families:
                problems.append(f"{rid} : famille inconnue {rule.family!r}")
            for name in list(rule.params) + list(rule.when_off):
                if name not in table:
                    problems.append(f"{rid} : paramètre inconnu {name!r}")
            for name in rule.when_off:
                if name not in rule.params:
                    problems.append(f"{rid} : `when_off` porte sur {name!r}, absent de ses paramètres")
            for name in rule.params:
                if name in seen:
                    problems.append(f"{name} appartient à deux règles : {seen[name]} et {rid}")
                seen[name] = rid
            for ref in rule.refs:
                if ref not in self.references:
                    problems.append(f"{rid} : référence inconnue {ref!r}")
            if rule.toggle and _known(rule, table) and not self.off_values(rid, table):
                problems.append(f"{rid} : règle désactivable sans valeur d'extinction (`when_off` ou `neutral`)")
        missing = sorted(set(table) - set(seen))
        if missing:
            problems.append(f"paramètres sans règle : {', '.join(missing)}")
        if problems:
            raise RuleError("catalogue des règles invalide :\n- " + "\n- ".join(problems))


def _known(rule: Rule, table: Mapping[str, Parameter]) -> bool:
    return all(name in table for name in rule.params)


def switch_off(current: Any, off: Any) -> Any:
    """A dict switch-off value replaces only its keys of the current value."""
    if isinstance(off, Mapping) and isinstance(current, Mapping):
        return {**current, **off}
    return off


@lru_cache(maxsize=1)
def load_catalogue() -> Catalogue:
    data = resources.files("nichd_sim.data")
    raw = yaml.safe_load(data.joinpath("rules.yaml").read_text(encoding="utf-8"))
    refs = yaml.safe_load(data.joinpath("references.yaml").read_text(encoding="utf-8"))
    catalogue = Catalogue.model_validate({**raw, "references": refs})
    catalogue.validate_against(_default_table())
    return catalogue


class RuleConfig(BaseModel):
    """What the control panel sets for a session: rules switched off and adjusted values. Also the
    content of a named preset (YAML)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str = ""
    disabled: list[str] = []
    overrides: dict[str, Any] = {}
    """Parameter → value, or {age band → value} to change one band only."""

    @property
    def is_default(self) -> bool:
        return not self.disabled and not self.overrides

    def check(self, catalogue: Catalogue | None = None) -> RuleConfig:
        catalogue = catalogue or load_catalogue()
        table = _default_table()
        problems = [f"règle inconnue : {r}" for r in self.disabled if r not in catalogue.rules]
        problems += [f"la règle {r} ne se désactive pas" for r in self.disabled
                     if r in catalogue.rules and not catalogue.rules[r].toggle]
        problems += [f"paramètre inconnu : {p}" for p in self.overrides if p not in table]
        if problems:
            raise RuleError("; ".join(problems))
        return self

    def resolved_overrides(self, band: AgeBand, base: Mapping[str, Any] | None = None,
                           catalogue: Catalogue | None = None) -> dict[str, Any]:
        """Scenario overrides (`base`), then this configuration's values, then the rules switched off."""
        catalogue = catalogue or load_catalogue()
        self.check(catalogue)
        merged = {**(base or {}), **self.overrides}
        current = Parameters.load(band, merged)
        out = dict(merged)
        for rid in self.disabled:
            for name, off in catalogue.off_values(rid, current.table).items():
                out[name] = switch_off(current[name], off)
        return out

    def parameters(self, band: AgeBand, base: Mapping[str, Any] | None = None) -> Parameters:
        return Parameters.load(band, self.resolved_overrides(band, base))

    def summary(self) -> dict[str, Any]:
        """For the session log (the resolved values are in `parameters`)."""
        return {"preset": self.name, "disabled": sorted(self.disabled), "adjusted": sorted(self.overrides)}

    # -- presets --------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> RuleConfig:
        path = Path(path)
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            config = cls.model_validate(raw)
        except FileNotFoundError as e:
            raise RuleError(f"préréglage introuvable : {path}") from e
        except (yaml.YAMLError, ValidationError) as e:
            raise RuleError(f"{path.name} : préréglage illisible — {e}") from e
        if config.name is None:
            config.name = path.stem
        return config.check()

    def save(self, path: str | Path) -> Path:
        self.check()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(exclude_defaults=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path


def list_presets(directory: str | Path) -> dict[str, Path]:
    """Preset name → file, sorted by name."""
    directory = Path(directory)
    return {p.stem: p for p in sorted(directory.glob("*.yaml"))} if directory.is_dir() else {}
