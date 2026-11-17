"""Cost — latency per stage of a voice turn, and GPU memory (reported only).

    uv run python experiments/voice_eval/cost.py   # run with no other GPU load
"""

from __future__ import annotations

import statistics as st
import subprocess
import time

from checks import Check, save
from sim import corpus
from stats import quantile

from nichd_sim.classification import ClassificationContext
from nichd_sim.classifiers.llm import DEFAULT_CLASSIFIER_THINK, LLMClassifier
from nichd_sim.evaluation import load_scenarios, load_testset
from nichd_sim.llm import DEFAULT_MODEL, OllamaClient
from nichd_sim.realization import LLMRealizer
from nichd_sim.voice import KokoroSpeaker, render_speech
from nichd_sim.voice.listener import WhisperListener

N = 20


def gpu_mb() -> int:
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout
    return sum(int(x) for x in out.split())


def timed(fn, n=N):
    fn()  # warm-up (model loading excluded)
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t)
    return out


def main() -> None:
    replies = [r for r in corpus(range(1), styles=("mixte",)) if r.result.response.strip()][:N]
    items = load_testset()[:N]
    scenarios = load_scenarios()
    base = gpu_mb()
    lat = {}
    with KokoroSpeaker() as child, WhisperListener() as listener:
        it = iter(replies * 3)
        lat["synthèse (Kokoro, réponse entière)"] = timed(
            lambda: (lambda r: render_speech(r.result.speech_plan, child, r.decision.delivery))(next(it)))
        adult = KokoroSpeaker(child=False, share_with=child)
        clips = [adult.synthesize(i["utterance"]) for i in items]
        ic = iter(clips * 3)
        lat["transcription (Whisper large-v3)"] = timed(lambda: listener.transcribe(next(ic)))
        voice_mb = gpu_mb() - base
    think = False if DEFAULT_CLASSIFIER_THINK in ("off", "false", "0") else DEFAULT_CLASSIFIER_THINK
    clf = LLMClassifier(OllamaClient(DEFAULT_MODEL), think=think)
    ii = iter(items * 3)
    lat[f"classification ({DEFAULT_MODEL}, réflexion {DEFAULT_CLASSIFIER_THINK})"] = timed(
        lambda: (lambda i: clf.classify(i["utterance"], ClassificationContext(scenario=scenarios[i["scenario"]])))(next(ii)),
        n=10)
    realizer = LLMRealizer(OllamaClient(DEFAULT_MODEL))
    ir = iter(replies * 3)
    lat[f"réalisation ({DEFAULT_MODEL})"] = timed(
        lambda: (lambda r: realizer.realize(r.decision, _profile(r), [("interviewer", "Raconte.")]))(next(ir)),
        n=10)
    checks = [Check("coût", f"Latence, {k}", f"p50 {st.median(v):.2f} s, p95 {quantile(v, 0.95):.2f} s",
                    "rapporté", None, f"{len(v)} mesures") for k, v in lat.items()]
    total = sum(st.median(v) for v in lat.values())
    checks.append(Check("coût", "Tour vocal complet (somme des médianes, hors silence simulé)", f"{total:.1f} s",
                        "rapporté", None, "optimisation prévue plus tard"))
    checks.append(Check("coût", "Mémoire GPU des modèles vocaux (Kokoro + Whisper)", f"{voice_mb / 1024:.1f} Go",
                        "rapporté", None))
    save("cost", checks)


def _profile(r):
    from sim import scenarios

    return next(s for s in scenarios() if s.id == r.scenario).child_profile


if __name__ == "__main__":
    main()
