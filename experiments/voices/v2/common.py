"""Shared by the v2 synthesis workers (plain Python: each engine runs in its own venv)."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
REF = HERE / "references"
RES = HERE / "results"
AUDIO = RES / "audio"

# Whole replies, synthesized in one go with their hesitations written in the text ("native" mode),
# to compare with the spliced mode (fragments cut at pauses, silences inserted).
REPLIES = [
    {"id": "r01", "text": "Euh… je sais pas trop."},
    {"id": "r02", "text": "C'était dimanche soir… on était dans la cuisine."},
    {"id": "r03", "text": "Il… il m'a attrapé le bras très fort."},
    {"id": "r04", "text": "Non."},
    {"id": "r05", "text": "Euh… après je suis allée dans ma chambre, et… j'avais un bleu sur le bras."},
    {"id": "r06", "text": "Oui. C'était mardi après l'école, vers cinq heures."},
    {"id": "r07", "text": "J'aime bien jouer à cache-cache et faire du vélo !"},
    {"id": "r08", "text": "Je… je veux pas trop en parler."},
    {"id": "r09", "text": "Karim a crié très fort sur moi, et puis il m'a tapé dans le dos avec sa main."},
    {"id": "r10", "text": "Hein ? Je comprends pas."},
    {"id": "r11", "text": "Il l'a déjà fait d'autres fois… quand maman n'est pas là."},
    {"id": "r12", "text": "D'accord, merci."},
]


def segments() -> list[dict]:
    """The v1 corpus: what the engine really sends to the voice, fragments included."""
    return json.loads((HERE.parent / "results" / "corpus.json").read_text(encoding="utf-8"))


def items() -> list[dict]:
    return segments() + REPLIES


def references() -> dict[str, dict]:
    return {r["id"]: r for r in json.loads((REF / "references.json").read_text(encoding="utf-8"))}


def add_reference(entry: dict) -> None:
    refs = references()
    refs[entry["id"]] = entry
    (REF / "references.json").write_text(json.dumps(list(refs.values()), ensure_ascii=False, indent=1), encoding="utf-8")


def write_rows(engine: str, meta: dict, rows: list[dict]) -> None:
    RES.mkdir(parents=True, exist_ok=True)
    (RES / f"synth_{engine}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [dict(meta, engine=engine), *rows]) + "\n")
