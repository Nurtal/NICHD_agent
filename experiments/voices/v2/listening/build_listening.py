"""Build the blind listening pack from the v2 screening (run with the project env: uv run python …).

- Baselines on the same replies: the current voice through the current assembly (Kokoro child, reply
  cut at « … », silences inserted), and the same with the new assembly (room tone, longer fades).
- Candidates: for each engine, the clean child-like clone (≤ 3 % hallucinations, ≤ 8 % WER on whole replies)
  whose pitch is closest to 300 Hz (else the fewest hallucinations), the best adult-reference clone overall, and one emotion variant.
Clips are loudness-matched (RMS) 24 kHz mono, renamed at random; design.json keeps the mapping (hidden).
"""

from __future__ import annotations

import json
import random
import sys
from array import array
from pathlib import Path

HERE = Path(__file__).parent
V2 = HERE.parent
sys.path.insert(0, str(V2))
from common import AUDIO, REPLIES, RES  # noqa: E402

from nichd_sim.delivery import ChunkKind, SpeechChunk  # noqa: E402
from nichd_sim.voice import Audio, make_speaker, render_speech  # noqa: E402
from nichd_sim.voice.render import NATURAL_STYLE  # noqa: E402

GROUPS = ["r03", "r05", "r07", "r08", "r09", "r11"]
CHILD_REFS = ("synth_qwen_girl8", "synth_qwen_boy6", "synth_kokoro_child")
SR = 24000


def current_plan(text: str) -> list[SpeechChunk]:
    """The current assembly: onset silence, pieces cut at « … », silences in between."""
    plan = [SpeechChunk(kind=ChunkKind.SILENCE, ms=700)]
    pieces = [p.strip() for p in text.replace("Euh…", "euh… ").split("…") if p.strip()]
    for i, p in enumerate(pieces):
        if i:
            plan.append(SpeechChunk(kind=ChunkKind.SILENCE, ms=550))
        plan.append(SpeechChunk(kind=ChunkKind.SPEECH, text=p))
    return plan


def matched(audio: Audio, target_rms: float = 2600.0) -> Audio:
    a = audio.resampled(SR) if audio.sample_rate != SR else audio
    s = a.samples
    rms = (sum(x * x for x in s) / max(1, len(s))) ** 0.5 or 1.0
    g = target_rms / rms
    return Audio(SR, array("h", (max(-32767, min(32767, int(x * g))) for x in s)))


def choose(summary: list[dict]) -> list[str]:
    def key(r):
        return (r["halluc"] / max(1, r["n"]), r["wer_replies"])
    picked = []
    engines = sorted({r["engine"] for r in summary if r["engine"] != "v1"})
    for e in engines:
        rows = [r for r in summary if r["engine"] == e and "+" not in r["variant"] and r["pauses"] != "—"]
        child = [r for r in rows if r["variant"].endswith(CHILD_REFS)]
        clean = [r for r in child if r["halluc"] / max(1, r["n"]) <= 0.03 and r["wer_replies"] <= 0.08 and r["f0"]]
        if clean:  # a child's voice: the clean clone whose pitch is closest to an 8-year-old's (~300 Hz)
            picked.append(min(clean, key=lambda r: abs(r["f0"] - 300))["variant"])
        elif child:
            picked.append(min(child, key=key)["variant"])
        elif rows:
            picked.append(min(rows, key=key)["variant"])
    adults = [r for r in summary if r["engine"] != "v1" and not r["variant"].endswith(CHILD_REFS)
              and "+" not in r["variant"] and "peur" not in r["variant"] and "tristesse" not in r["variant"]
              and r["pauses"] != "—"]
    if adults:
        best = min(adults, key=key)["variant"]
        if best not in picked:
            picked.append(best)
    designed = "qwen-synth_qwen_girl8"  # the designed 8-year-old girl, as Qwen itself renders her
    if designed not in picked and any(r["variant"] == designed for r in summary):
        picked.append(designed)
    emo = [r for r in summary if "+fear" in r["variant"]]
    if emo:
        picked.append(emo[0]["variant"])
    return picked


def main() -> None:
    summary = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
    variants = choose(summary)
    texts = {r["id"]: r["text"] for r in REPLIES}
    clips_dir = HERE / "clips"
    clips_dir.mkdir(exist_ok=True)
    for old in clips_dir.glob("*.wav"):  # a rebuild replaces the whole pack
        old.unlink()
    rng = random.Random(20261117)
    design = {"clips": {}, "variants": ["kokoro-actuel", "kokoro-actuel+fond"] + variants}
    groups = []
    speaker = make_speaker("kokoro")
    for gid in GROUPS:
        clips = []
        sources = {}
        r_cur = render_speech(current_plan(texts[gid]), speaker)
        sources["kokoro-actuel"] = r_cur.audio
        sources["kokoro-actuel+fond"] = render_speech(current_plan(texts[gid]), speaker, style=NATURAL_STYLE).audio
        for v in variants:
            path = AUDIO / v / f"{gid}.wav"
            if path.exists():
                sources[v] = Audio.read_wav(path)
        for v, audio in sources.items():
            name = f"x{rng.randrange(16 ** 6):06x}"
            matched(audio).write_wav(clips_dir / f"{name}.wav")
            design["clips"][name] = {"variant": v, "reply": gid}
            clips.append(name)
        groups.append({"id": gid, "text": texts[gid], "clips": clips})
        print(gid, len(clips), "voix", file=sys.stderr)
    (HERE / "tasks.json").write_text(json.dumps({"version": "v2-1", "groups": groups}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    (HERE / "design.json").write_text(json.dumps(design, ensure_ascii=False, indent=1), encoding="utf-8")
    print("variantes :", design["variants"])


if __name__ == "__main__":
    main()
