"""A metric, its value and its acceptance threshold: one row of the evaluation report."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

RESULTS = Path(__file__).parent / "results"


@dataclass
class Check:
    level: str
    metric: str
    value: float | str
    target: str
    ok: bool | None
    """None: reported only (no threshold), or indicative."""
    note: str = ""

    def row(self) -> str:
        v = f"{self.value:.3g}" if isinstance(self.value, float) else str(self.value)
        mark = {True: "✅", False: "❌", None: "—"}[self.ok]
        return f"| {self.metric} | {v} | {self.target} | {mark} | {self.note} |"


def save(level: str, checks: list[Check], extra: dict | None = None) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{level}.json"
    path.write_text(json.dumps({"checks": [asdict(c) for c in checks], **(extra or {})}, ensure_ascii=False,
                               indent=1), encoding="utf-8")
    for c in checks:
        print(c.row())
    return path
