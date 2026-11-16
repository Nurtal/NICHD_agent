"""N3, stage 1 — Transcription of the interviewer: the 104 test utterances of the NICHD skill,
spoken by synthetic speakers (OPTIMISTIC: real voices are harder), clean and with noise.

    uv run python experiments/voice_eval/n3_stt.py

Real recordings, when available, go in experiments/voice_eval/recordings/<id>.wav (e.g. ts001.wav):
they are then used as an extra speaker "réel", with no other change.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from checks import RESULTS, Check, save
from n4_turn_taking import with_noise
from stats import edit_distance

from nichd_sim.evaluation import load_testset
from nichd_sim.text import normalize
from nichd_sim.voice import Audio, KokoroSpeaker
from nichd_sim.voice.listener import WhisperListener

HERE = Path(__file__).parent
RECORDINGS = HERE / "recordings"
SPEAKERS = {  # pseudo-speakers from the only French Kokoro voice: pitch/formant factor, rate
    "grave-lent": (0.85, 0.9),
    "moyen": (1.0, 1.0),
    "aigu-rapide": (1.1, 1.15),
}
SNRS = [None, 20, 10, 5]


def wer(ref: str, hyp: str) -> tuple[int, int]:
    r, h = normalize(ref).split(), normalize(hyp).split()
    return edit_distance(r, h), len(r)


def proper_names(text: str) -> list[str]:
    """Capitalized words that are not sentence-initial (names: Léo, Karim, Monsieur Bertin…)."""
    words = re.findall(r"[\w'-]+", text)
    return [w for i, w in enumerate(words) if i > 0 and w[0].isupper() and words[i - 1][-1] not in ".!?"]


def main() -> None:
    items = load_testset()
    rng = random.Random(0)
    rows = []
    with KokoroSpeaker(child=False) as base, WhisperListener() as listener:
        voices = {}
        for name, (factor, rate) in SPEAKERS.items():
            sp = KokoroSpeaker(child=False, share_with=base)
            sp.factor = factor
            voices[name] = (sp, rate)
        for item in items:
            sources = {name: _say(sp, item["utterance"], rate) for name, (sp, rate) in voices.items()}
            real = RECORDINGS / f"{item['id']}.wav"
            if real.exists():
                sources["réel"] = Audio.read_wav(real)
            for name, audio in sources.items():
                for snr in SNRS if name in ("moyen", "réel") else [None]:
                    t = listener.transcribe(with_noise(audio, snr, rng)).text
                    errs, n = wer(item["utterance"], t)
                    names = proper_names(item["utterance"])
                    rows.append({"id": item["id"], "speaker": name, "snr": snr, "utterance": item["utterance"],
                                 "transcript": t, "errors": errs, "words": n,
                                 "names": len(names), "names_ok": sum(normalize(x) in normalize(t) for x in names)})
    (RESULTS / "n3_transcripts.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    def agg(rs):
        return sum(r["errors"] for r in rs) / max(1, sum(r["words"] for r in rs))

    checks = []
    for name in list(SPEAKERS) + (["réel"] if any(r["speaker"] == "réel" for r in rows) else []):
        rs = [r for r in rows if r["speaker"] == name and r["snr"] is None]
        w = agg(rs)
        short = agg([r for r in rs if r["words"] <= 3])
        checks.append(Check("N3", f"WER, locuteur « {name} », sans bruit", w, "< 0,10", w < 0.10,
                            f"énoncés ≤ 3 mots : {short:.1%} ; {'synthétique, optimiste' if name != 'réel' else 'voix réelle'}"))
    for snr in SNRS[1:]:
        rs = [r for r in rows if r["speaker"] == "moyen" and r["snr"] == snr]
        checks.append(Check("N3", f"WER, locuteur « moyen », {snr} dB", agg(rs), "rapporté", None,
                            f"énoncés ≤ 3 mots : {agg([r for r in rs if r['words'] <= 3]):.1%}"))
    clean = [r for r in rows if r["snr"] is None]
    names = sum(r["names"] for r in clean)
    checks.append(Check("N3", "Noms propres correctement transcrits (sans bruit)",
                        sum(r["names_ok"] for r in clean) / max(1, names), "rapporté", None, f"{names} occurrences"))
    worst = sorted((r for r in clean if r["words"]), key=lambda r: -r["errors"] / r["words"])[:15]
    save("n3_stt", checks, {"worst": [{k: r[k] for k in ("id", "speaker", "utterance", "transcript")} for r in worst]})


def _say(sp: KokoroSpeaker, text: str, rate: float) -> Audio:
    a = Audio.silence(24000, 300)
    a.extend(sp.synthesize(text, rate=rate))
    a.extend(Audio.silence(24000, 300))
    return a


if __name__ == "__main__":
    main()
