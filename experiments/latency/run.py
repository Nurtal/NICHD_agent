"""Latency of a live voice turn, stage by stage (plan « fluidité en direct », lot L0).

    uv run python experiments/latency/run.py --label base --out docs/evaluations/latence.md

Each interviewer line of scripts/*.txt is spoken by the adult Kokoro voice, then goes through the whole chain:
Whisper → classifier → engine → realizer → output filter → child voice (synthesis + pause re-timing).
Stages run one after the other, as in a live turn. Time to first sound = sum of the compute stages (the child's
planned silence before speaking is part of the simulation and is reported apart).

Shared GPUs: one LLM only (the classifier's model also realizes), unloaded at the end."""

from __future__ import annotations

import argparse
import json
import statistics as st
import subprocess
import time
import urllib.request
from pathlib import Path

from nichd_sim.classifiers.llm import LLMClassifier
from nichd_sim.cli import parse_think
from nichd_sim.llm import DEFAULT_MODEL, DEFAULT_URL, OllamaClient
from nichd_sim.realization import LLMRealizer
from nichd_sim.scenario import load_scenario
from nichd_sim.session import Session
from nichd_sim.voice import KokoroSpeaker, make_speaker, render_speech
from nichd_sim.voice.listener import WhisperListener

HERE = Path(__file__).parent
SCRIPTS = sorted((HERE / "scripts").glob("*.txt"))
NOTES = "## Constats"  # hand-written section of the report, kept when the tables are rewritten
STAGES = ["stt", "classification", "realization", "synthesis", "render", "first_sound"]
LABELS = {
    "stt": "Transcription (Whisper large-v3)",
    "classification": "Classification",
    "realization": "Réalisation (avec filtre et reprise)",
    "synthesis": "Synthèse de la voix",
    "render": "Recalage des pauses et ambiance",
    "first_sound": "**Jusqu'au premier son**",
}


class TimedSpeaker:
    """Wraps a speaker to time the synthesis apart from the re-timing done around it."""

    def __init__(self, inner):
        self.inner = inner
        self.native = getattr(inner, "native", False)
        self.spent = 0.0

    def synthesize(self, text, *, rate=1.0):
        t = time.perf_counter()
        try:
            return self.inner.synthesize(text, rate=rate)
        finally:
            self.spent += time.perf_counter() - t

    def __getattr__(self, name):
        return getattr(self.inner, name)


def gpu() -> str:
    return subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip().replace("\n", " / ")


def ollama_ps(url: str) -> list[dict]:
    with urllib.request.urlopen(f"{url}/api/ps") as r:
        return json.loads(r.read()).get("models", [])


def unload(url: str, model: str) -> None:
    req = urllib.request.Request(f"{url}/api/generate", data=json.dumps({"model": model, "keep_alive": 0}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()


def quantile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(q * (len(xs) - 1)))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--think", default="medium")
    ap.add_argument("--speaker", default=None, help="child voice (default: the best installed)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", type=Path, help="markdown report to (re)write")
    args = ap.parse_args()
    results = HERE / "results"
    results.mkdir(exist_ok=True)

    # 1. The learner's lines, spoken once (Kokoro adult voice), cached.
    clips_dir = results / "clips"
    clips_dir.mkdir(exist_ok=True)
    scripts = {p.stem: [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] for p in SCRIPTS}
    from nichd_sim.voice import Audio

    missing = [(s, i, u) for s, lines in scripts.items() for i, u in enumerate(lines)
               if not (clips_dir / f"{s}_{i:02d}.wav").exists()]
    if missing:
        with KokoroSpeaker(child=False) as adult:
            for s, i, u in missing:
                adult.synthesize(u).write_wav(clips_dir / f"{s}_{i:02d}.wav")

    rows: list[dict] = []
    cold: dict[str, float] = {}
    gpu_seen = []
    client = OllamaClient(args.model, keep_alive="10m", timeout=300)
    t = time.perf_counter()
    client.chat([{"role": "user", "content": "ok"}], temperature=0, think=False)
    cold["chargement du LLM"] = time.perf_counter() - t
    with WhisperListener() as listener:
        t = time.perf_counter()
        listener.transcribe(Audio.read_wav(next(clips_dir.glob("*.wav"))))
        cold["chargement de Whisper"] = time.perf_counter() - t
        for scen, lines in scripts.items():
            sc = load_scenario(Path("scenarios") / f"{scen}.yaml")
            speaker = make_speaker(args.speaker, sc.child_profile)
            timed = TimedSpeaker(speaker)
            t = time.perf_counter()
            timed.synthesize("Oui.")
            cold.setdefault(f"chargement de la voix ({type(speaker).__name__})", time.perf_counter() - t)
            clf = LLMClassifier(client, think=parse_think(args.think))
            session = Session(sc, clf, LLMRealizer(client, seed=args.seed), seed=args.seed)
            for i, _ in enumerate(lines):
                clip = Audio.read_wav(clips_dir / f"{scen}_{i:02d}.wav")
                t = time.perf_counter()
                heard = listener.transcribe(clip).text
                stt = time.perf_counter() - t
                t = time.perf_counter()
                res = session.turn(heard)
                engine_total = time.perf_counter() - t
                rec = session.log.turns[-1]
                meta = rec.classification.meta
                timed.spent = 0.0
                t = time.perf_counter()
                rendered = render_speech(res.speech_plan, timed, res.decision.delivery) if res.response.strip() else None
                tts_total = time.perf_counter() - t
                clf_s = rec.latency_s.get("classification", 0.0)
                row = {
                    "scenario": scen, "turn": i, "heard": heard, "response": res.response,
                    "stt": stt, "classification": clf_s, "realization": engine_total - clf_s,
                    "synthesis": timed.spent, "render": tts_total - timed.spent,
                    "onset_ms": rendered.onset_ms if rendered else None,
                    "audio_ms": rendered.audio.duration_ms if rendered else 0,
                    "fallback": res.fallback_used, "meta": meta,
                }
                row["first_sound"] = sum(row[k] for k in STAGES[:-1])
                rows.append(row)
                print(f"{scen} {i:2d}  " + "  ".join(f"{k[:5]} {row[k]:5.1f}" for k in STAGES), flush=True)
            gpu_seen.append(gpu())
            if hasattr(speaker, "close"):
                speaker.close()
    ps = ollama_ps(DEFAULT_URL)
    prompt_tokens = [r["meta"].get("prompt_eval_count") for r in rows if r["meta"].get("prompt_eval_count")]
    unload(DEFAULT_URL, args.model)

    out = results / f"{args.label}.json"
    out.write_text(json.dumps({"label": args.label, "model": args.model, "think": args.think, "cold_s": cold,
                               "ollama_ps": ps, "gpu": gpu_seen, "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"→ {out}")
    if args.out:
        write_report(args.out)


def summary(rows: list[dict]) -> dict[str, tuple[float, float]]:
    return {k: (st.median(r[k] for r in rows), quantile([r[k] for r in rows], 0.95)) for k in STAGES}


def write_report(path: Path) -> None:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "results").glob("*.json"))]
    runs.sort(key=lambda r: r.get("order", 0))
    lines = ["# Latence d'un tour vocal en direct", "",
             "Mesure : `experiments/latency/run.py`. 29 répliques de l'interviewer (s01, s08), dites par la voix adulte "
             "Kokoro, puis toute la chaîne : Whisper, classifieur, moteur, réalisateur, filtre, voix de l'enfant. "
             "Les étapes s'enchaînent comme en direct. « Jusqu'au premier son » est la somme du calcul ; le silence que "
             "le moteur prévoit avant que l'enfant parle (diction) n'y est pas compté.", ""]
    head = "| Étape | " + " | ".join(f"{r['label']} (méd. / p95)" for r in runs) + " |"
    lines += [head, "|---" * (len(runs) + 1) + "|"]
    sums = [summary(r["rows"]) for r in runs]
    for k in STAGES:
        lines.append(f"| {LABELS[k]} | " + " | ".join(f"{s[k][0]:.1f} s / {s[k][1]:.1f} s" for s in sums) + " |")
    lines.append("")
    for r in runs:
        onset = [x["onset_ms"] for x in r["rows"] if x["onset_ms"] is not None]
        toks = [x["meta"].get("prompt_eval_count") for x in r["rows"] if x["meta"].get("prompt_eval_count")]
        ctx = ", ".join(f"{m['name']} contexte {m.get('context_length', '?')}" for m in r.get("ollama_ps", []))
        lines += [f"**{r['label']}** — modèle `{r['model']}`, réflexion `{r['think']}`. "
                  f"Démarrage à froid : " + ", ".join(f"{k} {v:.1f} s" for k, v in r["cold_s"].items()) + ". "
                  f"Silence prévu avant la parole : médiane {st.median(onset):.0f} ms. "
                  + (f"Invite du classifieur : {min(toks)}–{max(toks)} jetons ({ctx}). " if toks else "")
                  + f"Replis du réalisateur : {sum(x['fallback'] for x in r['rows'])} / {len(r['rows'])}. "
                  f"GPU pendant la mesure : {r['gpu'][-1]}.", ""]
    notes = path.read_text(encoding="utf-8").split(NOTES, 1)[1] if path.exists() and NOTES in path.read_text(encoding="utf-8") else "\n"
    path.write_text("\n".join(lines) + "\n" + NOTES + notes, encoding="utf-8")
    print(f"→ {path}")


if __name__ == "__main__":
    main()
