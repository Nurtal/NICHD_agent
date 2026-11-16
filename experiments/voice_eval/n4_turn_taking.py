"""N4 — Turn-taking and interruptions, with a synthetic ground truth.

Learner recordings are built so that the true speech start is known: digital silence of L ms, then
the interviewer's speech (adult Kokoro voice, trimmed), then optional white noise at a given SNR.
Each exchange is placed `after_ms` ∈ [−6 s, +3 s] after the child's previous reply. The truth
(interruption moment, units not said) is computed from the exact rendered timeline at the TRUE
start; the system's output comes from its energy-based detection. So N4 measures how much timing
errors (and noise) distort interruptions and the engine's rollback.

    uv run python experiments/voice_eval/n4_turn_taking.py [--sessions 12]
"""

from __future__ import annotations

import argparse
import math
import random
import statistics as st
from array import array

from checks import Check, save
from sim import _question, scenarios
from stats import quantile

from doubles import C, ScriptedClassifier, ask, make_session
from nichd_sim.realization import TemplateRealizer
from nichd_sim.session import Session
from nichd_sim.text import mentions, normalize
from nichd_sim.voice import Audio, KokoroSpeaker
from nichd_sim.voice.conversation import VoiceConversation, barge_in_at
from nichd_sim.voice.listener import WhisperListener

PROMPTS = [
    "Dis-moi tout ce qui s'est passé.", "Et après ?", "Raconte-moi encore.", "Hmm hmm.",
    "Tu m'as parlé de ça, dis-m'en plus.", "Qu'est-ce qui s'est passé ensuite ?", "Qui était là ?",
    "C'était où ?", "Tu peux tout me dire.", "Et puis ?", "Comment ça s'est terminé ?", "D'accord.",
]
SNRS = [None, 20, 10, 5]
"""5 dB: very noisy, reported without threshold."""


def with_noise(audio: Audio, snr_db: float | None, rng: random.Random) -> Audio:
    if snr_db is None:
        return audio
    voiced = [s for s in audio.samples if abs(s) > 300] or [1]
    rms = math.sqrt(sum(s * s for s in voiced) / len(voiced))
    sigma = rms / 10 ** (snr_db / 20)
    return Audio(audio.sample_rate, array("h", (max(-32768, min(32767, int(s + rng.gauss(0, sigma))))
                                                for s in audio.samples)))


def true_unheard(session: Session, turn_index: int, heard_text: str) -> list[str]:
    """Units of that reply not mentioned in the truly heard text (same rule as the session)."""
    heard = normalize(heard_text)
    out = []
    for au in session.log.turns[turn_index].decision.allowed_units:
        unit = session.scenario.unit(au.id)
        if au.contaminated or au.lie or not au.new or unit is None:
            continue
        if not any(mentions(heard, a) for a in unit.anchors):
            out.append(au.id)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=12)
    ap.add_argument("--turns", type=int, default=9)
    args = ap.parse_args()
    rng = random.Random(0)
    scs = scenarios(deception_variants=False)
    rows = []
    with KokoroSpeaker() as child, WhisperListener() as listener:
        adult = KokoroSpeaker(child=False, share_with=child)
        voices = {p: adult.synthesize(p).trimmed(margin_ms=0) for p in PROMPTS}
        for snr in SNRS:
            for k in range(args.sessions):
                sc = scs[k % len(scs)]
                clf = ScriptedClassifier()
                session = Session(sc, clf, TemplateRealizer(), seed=k)
                conv = VoiceConversation(session, child, listener)
                prev = None
                for t in range(args.turns):
                    c = (C("invitation", phase_hints=["transition"]) if t < 2
                         else _question(rng, sc, "ouvert", session.state.revealed))
                    lead = rng.randint(100, 600)
                    rec = Audio.silence(voices[PROMPTS[0]].sample_rate, lead)
                    rec.extend(voices[rng.choice(PROMPTS)])
                    rec.extend(Audio.silence(rec.sample_rate, 200))
                    rec = with_noise(rec, snr, rng)
                    after = rng.randint(-6000, 3000) if prev is not None else 500
                    clf.script = {}
                    clf.classify = lambda u, ctx, c=c: c  # scripted by order, whatever the transcript
                    try:
                        ex = conv.exchange(rec, after)
                    except ValueError:  # nothing heard
                        rows.append({"snr": snr, "missed": True})
                        break
                    true_wait = after + lead
                    row = {"snr": snr, "missed": False, "wait_err": abs(ex.timing.wait_ms - true_wait),
                           "true_kind": "none", "kind": ex.timing.barge_in.during if ex.timing.barge_in else "none"}
                    if prev is not None and true_wait < 0:
                        truth = barge_in_at(prev, prev.audio.duration_ms + true_wait)
                        row["true_kind"] = truth.during
                        row["true_unheard"] = true_unheard(session, len(session.log.turns) - 2, truth.heard_text)
                        row["unheard"] = session.log.turns[-2].unheard_units
                    rows.append(row)
                    prev = ex.child
        # false positives: recordings without speech
        fps = []
        for level_db in (None, -50, -40, -30):
            for _ in range(10):
                noise = Audio.silence(24000, 2000)
                if level_db is not None:
                    sigma = 32768 * 10 ** (level_db / 20)
                    noise = Audio(24000, array("h", (int(rng.gauss(0, sigma)) for _ in range(48000))))
                text = listener.transcribe(noise).text.strip()
                fps.append(bool(text))

    checks = []
    for snr in SNRS:
        rs = [r for r in rows if r["snr"] == snr and not r["missed"]]
        label = "propre" if snr is None else f"{snr} dB"
        err = [r["wait_err"] for r in rs]
        limit = 50 if snr is None or snr >= 20 else 100
        judged = snr is None or snr >= 10
        checks.append(Check("N4", f"Erreur sur l'instant de prise de parole, {label} (ms, moyenne)", st.fmean(err),
                            f"< {limit}" if judged else "rapporté", st.fmean(err) < limit if judged else None,
                            f"p95 = {quantile(err, 0.95):.0f} ms ; {len(rs)} échanges"))
        acc = sum(r["kind"] == r["true_kind"] for r in rs) / len(rs)
        checks.append(Check("N4", f"Moment de l'interruption bien classé (aucune / silence initial / pause / phrase), {label}",
                            acc, "≥ 0,95" if judged else "rapporté", acc >= 0.95 if judged else None))
        tp = fp = fn = 0
        for r in rs:
            if "true_unheard" in r:
                t_, s_ = set(r["true_unheard"]), set(r["unheard"])
                tp, fp, fn = tp + len(t_ & s_), fp + len(s_ - t_), fn + len(t_ - s_)
        prec = tp / (tp + fp) if tp + fp else 1.0
        rec = tp / (tp + fn) if tp + fn else 1.0
        checks.append(Check("N4", f"Unités non dites : précision / rappel, {label}", f"{prec:.2f} / {rec:.2f}",
                            "≥ 0,95 / ≥ 0,95" if judged else "rapporté",
                            prec >= 0.95 and rec >= 0.95 if judged else None, f"{tp + fn} unités coupées"))
        missed = sum(r["missed"] for r in rows if r["snr"] == snr)
        checks.append(Check("N4", f"Énoncés non entendus (rejetés), {label}", missed, "0", missed == 0))
    fpr = sum(fps) / len(fps)
    checks.append(Check("N4", "Faux positifs : enregistrements sans parole pris pour un énoncé", fpr, "< 0,02",
                        fpr < 0.02, "silence et bruit blanc à −50, −40, −30 dBFS"))
    checks.append(coherence())
    confusion = {}
    for r in rows:
        if not r["missed"]:
            confusion[f"{r['true_kind']}→{r['kind']}"] = confusion.get(f"{r['true_kind']}→{r['kind']}", 0) + 1
    save("n4", checks, {"confusion": confusion, "exchanges": len(rows)})


def coherence() -> Check:
    """Same classifications, text session vs voice conversation without interruption: same decisions."""
    from nichd_sim.voice import ToneSpeaker

    class Hears:  # fixed transcript: the voice path minus Whisper
        def transcribe(self, audio, *, prompt=None):
            from nichd_sim.voice.listener import Transcript, Word
            return Transcript("Dis-moi.", [Word("Dis-moi.", 100, audio.duration_ms)])

    same = total = 0
    rng = random.Random(1)
    for k, sc in enumerate(scenarios(deception_variants=False)):
        script = [C("invitation", phase_hints=["transition"])] * 2 + [
            _question(rng, sc, "mixte", []) for _ in range(10)]
        text, clf, _ = make_session(sc, seed=k)
        for i, c in enumerate(script):
            ask(text, clf, f"u{i}", c)
        voice, vclf, _ = make_session(sc, seed=k)
        conv = VoiceConversation(voice, ToneSpeaker(sample_rate=16000), Hears())
        for c in script:
            vclf.classify = lambda u, ctx, c=c: c
            rec = Audio.silence(16000, 100)
            rec.extend(Audio(16000, array("h", [3000, -3000] * 4000)))
            conv.exchange(rec, 700)
        for a, b in zip(text.log.turns, voice.log.turns):
            total += 1
            same += a.decision == b.decision
        total += 1
        same += (text.end().feedback.metrics.accurate_info_recall == voice.end().feedback.metrics.accurate_info_recall)
    return Check("N4", "Cohérence texte/voix sans interruption (décisions et rappel identiques)", same / total, "1",
                 same == total, f"{total} comparaisons")


if __name__ == "__main__":
    main()
