"""Blind listening pack for the voice bank (run with the project env: uv run python …).

One group per slot (girl / boy × age band of the engine), one clip per candidate that passed the
objective check (bank_eval.py): two replies said one after the other. Clips are loudness-matched and
renamed at random. The previous pack (v2-1) is archived first: design_v2-1.json, ratings/v2-1/.
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
V2 = HERE.parent
sys.path.insert(0, str(V2))
sys.path.insert(0, str(HERE))
from build_listening import SR, matched
from common import REPLIES, RES

from nichd_sim.voice import Audio

BANK = RES / "bank"
VERSION = "bank-1"
SAY = ["r05", "r09"]
# Slot names follow the engine's age bands (scenario.AgeBand); the designs were described for 5–6,
# 8–9 and 11–12 years, inside those bands.
BANDS = {"5_7": ("4_6", "4 à 6 ans"), "8_10": ("7_9", "7 à 9 ans"), "11_12": ("10_12", "10 à 12 ans")}
GENDERS = {"fille": "Fille", "garcon": "Garçon"}


def archive_previous() -> None:
    design = HERE / "design.json"
    if not design.exists():
        return
    old = json.loads((HERE / "tasks.json").read_text(encoding="utf-8")).get("version", "ancien")
    if old == VERSION:
        return
    shutil.move(design, HERE / f"design_{old}.json")
    (HERE / "ratings" / old).mkdir(parents=True, exist_ok=True)
    for f in (HERE / "ratings").glob("*.json"):
        shutil.move(f, HERE / "ratings" / old / f.name)


def main() -> None:
    archive_previous()
    evals = json.loads((BANK / "bank_eval.json").read_text(encoding="utf-8"))
    texts = {r["id"]: r["text"] for r in REPLIES}
    clips_dir = HERE / "clips"
    clips_dir.mkdir(exist_ok=True)
    for old in clips_dir.glob("*.wav"):
        old.unlink()
    rng = random.Random(20261118)
    design = {"version": VERSION, "clips": {}}
    groups = []
    for gender, glabel in GENDERS.items():
        for band, (engine_band, blabel) in BANDS.items():
            slot = [e for e in evals if e["gender"] == gender and e["band"] == band and e["ok"]]
            if len(slot) < 2:
                continue  # nothing to choose (the validated girl 7–9 voice)
            clips = []
            for e in slot:
                audio = Audio(SR)
                for k, rid in enumerate(SAY):
                    if k:
                        audio.extend(Audio.silence(SR, 700))
                    a = Audio.read_wav(BANK / e["id"] / f"{rid}.wav")
                    audio.extend((a.resampled(SR) if a.sample_rate != SR else a).trimmed())
                name = f"x{rng.randrange(16 ** 6):06x}"
                matched(audio).write_wav(clips_dir / f"{name}.wav")
                design["clips"][name] = {"variant": e["id"], "reply": f"{gender}_{engine_band}"}
                clips.append(name)
            groups.append({"id": f"{gender}_{engine_band}", "title": f"{glabel}, {blabel}",
                           "text": " — ".join(texts[r] for r in SAY), "clips": clips})
            print(groups[-1]["title"], len(clips), "voix", file=sys.stderr)
    (HERE / "tasks.json").write_text(json.dumps({"version": VERSION, "groups": groups}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    (HERE / "design.json").write_text(json.dumps(design, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
