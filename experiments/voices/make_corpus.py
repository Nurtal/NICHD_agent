"""Corpus for the TTS screening: the speech chunks the engine really sends to a Speaker.

Runs the MVP fixture sessions and scripted s08 sessions (lies, retractions), takes the
speech-plan chunks of every child reply, dedups them. Run in the project env:

    uv run python experiments/voices/make_corpus.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from doubles import C, ask, make_session

from nichd_sim.delivery import FILLER, ChunkKind, plan_speech
from nichd_sim.replay import load_log
from nichd_sim.scenario import load_scenario

OUT = Path(__file__).parent / "results" / "corpus.json"
SIZE = 60


def s08_replies() -> list[tuple[str, object]]:
    out = []
    for seed in range(4):
        s, clf, _ = make_session(load_scenario(ROOT / "scenarios" / "s08_violences_maison_secret.yaml"), seed=seed)
        script = [C("support"), C("invitation", phase_hints=["transition"]), C("invitation"), C("invitation"),
                  C("directive", "d_karim"), C("option_posing", "d_bras", suggested_proposition="bras"),
                  C("support"), C("support"), C("support"), C("invitation"), C("invitation"),
                  C("invitation", phase_hints=["closure"])]
        for i, c in enumerate(script):
            r = ask(s, clf, f"u{i}", c)
            out.append((r.response, r.decision.delivery))
    return out


def main() -> None:
    replies = s08_replies()
    for path in sorted((ROOT / "tests" / "fixtures" / "mvp_logs").glob("*_0.json")):
        replies += [(t.response, None) for t in load_log(path).turns]
    chunks: dict[str, None] = {}
    for text, delivery in replies:
        for ch in plan_speech(text, delivery):
            if ch.kind == ChunkKind.SPEECH and ch.text != FILLER and any(c.isalpha() for c in ch.text):
                chunks[ch.text] = None
    items = sorted(chunks)
    rng = random.Random(0)
    rng.shuffle(items)
    # keep the short typical replies, then fill with narrative chunks
    must = [t for t in items if len(t.split()) <= 3][:12]
    rest = [t for t in items if t not in must][: SIZE - len(must)]
    corpus = [{"id": f"c{i:02d}", "text": t} for i, t in enumerate(must + rest)]
    corpus.append({"id": "filler", "text": FILLER})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(corpus)} segments → {OUT}")


if __name__ == "__main__":
    main()
