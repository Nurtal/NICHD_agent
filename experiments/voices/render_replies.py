"""Fragment fix check, step 1 (project env): render real replies with their pauses, two ways.

- `per-piece`: each speech chunk synthesized on its own (before the fix);
- `utterance`: the reply synthesized once and cut at the pause points (KokoroSpeaker default).

    uv run python experiments/voices/render_replies.py   # then eval_replies.py in the kokoro env
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from doubles import C, ask, make_session

from nichd_sim.delivery import ChunkKind
from nichd_sim.scenario import load_scenario
from nichd_sim.voice import KokoroSpeaker, render_speech

OUT = Path(__file__).parent / "results" / "replies"


class PerPiece:
    """Hides synthesize_pieces: forces the old one-synthesis-per-chunk path."""

    def __init__(self, inner):
        self.inner = inner
        self.sample_rate = inner.sample_rate

    def synthesize(self, text, *, rate=1.0):
        return self.inner.synthesize(text, rate=rate)


def replies():
    """Replies with at least one internal pause, from scripted sessions on several scenarios."""
    script = [C("support"), C("invitation", phase_hints=["transition"]), C("invitation", phase_hints=["transition"]),
              C("invitation"), C("invitation"), C("invitation"), C("facilitator"), C("invitation")]
    out = []
    for path in sorted((ROOT / "scenarios").glob("s0*.yaml")):
        for seed in range(3):
            s, clf, _ = make_session(load_scenario(path), seed=seed)
            for i, c in enumerate(script):
                r = ask(s, clf, f"u{i}", c)
                if sum(ch.kind == ChunkKind.SILENCE for ch in r.speech_plan) >= 2:
                    out.append((r.response, r.speech_plan, r.decision.delivery))
    seen, uniq = set(), []
    for item in out:
        if item[0] not in seen:
            seen.add(item[0])
            uniq.append(item)
    return uniq[:60]


def main() -> None:
    manifest = []
    with KokoroSpeaker() as sp:
        for mode, speaker in (("utterance", sp), ("per-piece", PerPiece(sp))):
            for i, (text, plan, delivery) in enumerate(replies()):
                r = render_speech(plan, speaker, delivery)
                wav = r.audio.write_wav(OUT / "audio" / mode / f"r{i:02d}.wav")
                manifest.append({"mode": mode, "id": f"r{i:02d}", "text": text, "wav": str(wav.relative_to(OUT)),
                                 "spans": [{"kind": str(s.kind), "start_ms": s.start_ms, "end_ms": s.end_ms,
                                            "text": s.text} for s in r.timeline]})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(manifest), "rendus")


if __name__ == "__main__":
    main()
