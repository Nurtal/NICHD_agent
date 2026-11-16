"""Command-line interface: play a session in the terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nichd_sim.classifiers.llm import DEFAULT_CLASSIFIER_THINK, LLMClassifier
from nichd_sim.classifiers.manual import HELP, ManualClassificationError, ManualClassifier
from nichd_sim.delivery import render_plan
from nichd_sim.feedback import LLMRephraser, LLMSummaryMatcher, render_text
from nichd_sim.phases import VIOLATION_LABELS
from nichd_sim.llm import DEFAULT_MODEL, DEFAULT_URL, LLMError, OllamaClient
from nichd_sim.realization import LLMRealizer, TemplateRealizer
from nichd_sim.replay import ReplayError, export_for_coders, find_scenario, load_log, replay
from nichd_sim.scenario import ScenarioError, load_scenario
from nichd_sim.session import Session

COMMANDS = """Commandes : /aide  /unites  /etat  /fin"""


def build_classifier(args: argparse.Namespace):
    if args.classifier == "manual":
        return ManualClassifier()
    if args.classifier == "llm":
        return LLMClassifier(
            OllamaClient(args.classifier_model or args.model, args.ollama_url), think=parse_think(args.classifier_think)
        )
    raise SystemExit(f"classifieur inconnu : {args.classifier}")


def parse_think(value: str) -> bool | str:
    """'off' → no thinking; otherwise an Ollama thinking level (low, medium, high)."""
    return False if value in ("off", "false", "0") else value


def build_realizer(args: argparse.Namespace):
    if args.realizer == "template":
        return TemplateRealizer()
    if args.realizer == "llm":
        return LLMRealizer(OllamaClient(args.model, args.ollama_url), seed=args.seed)
    raise SystemExit(f"realizer inconnu : {args.realizer}")


def play(args: argparse.Namespace) -> int:
    try:
        scenario = load_scenario(args.scenario)
    except ScenarioError as e:
        print(e, file=sys.stderr)
        return 2
    session = Session(
        scenario,
        build_classifier(args),
        build_realizer(args),
        seed=args.seed,
        log_dir=args.log_dir,
        rephraser=None if args.no_rephrase else LLMRephraser(OllamaClient(args.model, args.ollama_url)),
        summary_matcher=LLMSummaryMatcher(OllamaClient(args.model, args.ollama_url)) if args.summary else None,
    )
    child = scenario.child_profile.name
    speaker = None
    if args.voice:
        from nichd_sim.voice import make_speaker

        try:
            speaker = make_speaker(args.speaker)
        except (ValueError, RuntimeError) as e:
            print(e, file=sys.stderr)
            return 2
        print(f"Voix : {args.speaker or type(speaker).__name__}")
    print(f"=== {scenario.title} ===\n{scenario.intake_context.strip()}\n")
    if args.classifier == "manual":
        print(HELP)
    print(COMMANDS + "\n")
    while True:
        try:
            line = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line == "/fin":
            break
        if line == "/aide":
            print(HELP if args.classifier == "manual" else COMMANDS)
            continue
        if line == "/unites":
            for seg, u in scenario.all_units():
                print(f"  {u.id:<14} {seg:<7} {u.category:<10} {u.centrality}")
            continue
        if line == "/etat":
            print(session.state.model_dump_json(indent=2))
            continue
        try:
            result = session.turn(line)
        except ManualClassificationError as e:
            print(e)
            continue
        except LLMError as e:
            print(f"[erreur] {e}", file=sys.stderr)
            continue
        if args.trainer:
            c, d = result.classification, result.decision
            turn = session.log.turns[-1]
            inner = f" ({c.inner_type})" if c.inner_type else ""
            phase = f" [indice {c.phase_hints[0]}]" if c.phase_hints else ""
            print(
                f"  [formateur] {c.type}{inner}{' → ' + c.target if c.target else ''}{phase}"
                f" | {d.speech_act} | {d.reason} | phase {result.phase} | {turn.latency_s.get('total', 0):.1f}s"
            )
            if d.delivery is not None:
                print(f"  [formateur] diction : {d.delivery.describe()}")
            if d.lie is not None:
                print(f"  [formateur] mensonge {d.lie.id} ({d.lie.kind}) sur {d.lie.protected} : {d.lie.value!r}")
            if d.withheld:
                print(f"  [formateur] omis volontairement : {', '.join(d.withheld)}")
            if d.retraction is not None:
                print(f"  [formateur] revient sur {d.retraction.id} ({d.retraction.kind})")
            if session.scenario.deception is not None:
                print(f"  [formateur] dissimulation : {result.state.concealment:.2f}")
            for v in result.violations:
                print(f"  [formateur] ⚠ {VIOLATION_LABELS[v.kind]} : {v.phase}{' — ' + v.detail if v.detail else ''}")
            if c.suggested_proposition:
                print(f"  [formateur] proposition suggérée : {c.suggested_proposition}")
            if "error" in c.meta:
                print(f"  [formateur] classification en repli : {c.meta['error']}")
            for i, a in enumerate(turn.attempts):
                if not a.ok:
                    print(f"  [filtre] essai {i + 1} rejeté : {a.forbidden_terms + a.leaked_units + ['manque:' + m for m in a.missing_units] + (['vide'] if a.empty else []) + (['trop long'] if a.too_long else []) + (['contredit la décision'] if a.contradicts else []) + (['emoji'] if a.emoji else [])} — {a.text!r}")
            if turn.fallback_used:
                print("  [filtre] réponse de repli utilisée")
        print(f"{child} > {render_plan(result.speech_plan) if args.trainer else result.response}")
        if speaker is not None:
            from nichd_sim.voice import render_speech

            rendered = render_speech(result.speech_plan, speaker, result.decision.delivery)
            n = len(session.log.turns)
            path = rendered.audio.write_wav(Path(args.voice) / session.log.session_id / f"turn_{n:03d}.wav")
            print(f"  ♪ {path} ({rendered.audio.duration_ms / 1000:.1f} s, silence initial {rendered.onset_ms} ms)")
        for notice in result.notices:
            print(f"  ⓘ {notice}")
    summary = None
    if args.summary:
        print("\nRédigez votre synthèse de ce que l'enfant a dit (ligne vide pour terminer) :")
        lines = []
        while True:
            try:
                ln = input("  ")
            except EOFError:
                break
            if not ln.strip():
                break
            lines.append(ln)
        summary = " ".join(lines) or None
    log = session.end(learner_summary=summary)
    print(render_text(log.feedback))
    if args.log_dir:
        print(f"Journal : {Path(args.log_dir) / f'session_{session.log.session_id}.json'}")
    return 0


def replay_cmd(args: argparse.Namespace) -> int:
    try:
        log = load_log(args.log)
        scenario = load_scenario(args.scenario) if args.scenario else find_scenario(log, args.scenarios_dir)
    except (ReplayError, ScenarioError) as e:
        print(e, file=sys.stderr)
        return 2
    report = replay(log, scenario)
    if report.identical:
        print(f"Rejeu identique : {report.turns} tour(s), session {log.session_id}.")
        return 0
    print(f"Rejeu divergent ({len(report.mismatches)} écart(s)) :")
    for m in report.mismatches:
        print(f"  - {m}")
    return 1


def render_audio_cmd(args: argparse.Namespace) -> int:
    from nichd_sim.voice import make_speaker, render_log

    try:
        log = load_log(args.log)
        speaker = make_speaker(args.speaker)
    except (ReplayError, ValueError, RuntimeError) as e:
        print(e, file=sys.stderr)
        return 2
    out = Path(args.output or Path("audio") / log.session_id)
    paths = render_log(log, speaker, out)
    print(f"{len(paths)} fichier(s) audio dans {out}")
    return 0


def transcribe_cmd(args: argparse.Namespace) -> int:
    from nichd_sim.voice import Audio, VoiceError
    from nichd_sim.voice.listener import WhisperListener

    try:
        with WhisperListener() as listener:
            for path in args.wavs:
                t = listener.transcribe(Audio.read_wav(path))
                print(f"{path} : [{t.speech_start_ms}–{t.speech_end_ms} ms] {t.text}")
    except (VoiceError, ValueError, OSError) as e:
        print(e, file=sys.stderr)
        return 2
    return 0


def converse_cmd(args: argparse.Namespace) -> int:
    """Scripted voice conversation (YAML): interviewer turns as text (adult voice) or WAV."""
    import json

    import yaml

    from nichd_sim.voice import Audio, KokoroSpeaker, VoiceError, make_speaker
    from nichd_sim.voice.conversation import VoiceConversation
    from nichd_sim.voice.listener import WhisperListener

    spec = yaml.safe_load(Path(args.script).read_text(encoding="utf-8"))
    base = Path(args.script).parent
    out = Path(args.output)
    try:
        scenario = load_scenario(spec["scenario"])
    except ScenarioError as e:
        print(e, file=sys.stderr)
        return 2
    session = Session(scenario, build_classifier(args), build_realizer(args), seed=spec.get("seed", 0),
                      rephraser=None, log_dir=out)
    try:
        speaker = make_speaker(args.speaker)
        interviewer = (KokoroSpeaker(child=False, share_with=speaker) if isinstance(speaker, KokoroSpeaker)
                       else make_speaker("tone"))
        listener = WhisperListener()
        conv = VoiceConversation(session, speaker, listener)
        child = scenario.child_profile.name
        for i, turn in enumerate(spec["turns"], 1):
            if "wav" in turn:
                audio = Audio.read_wav(base / turn["wav"])
            else:
                audio = Audio.silence(24000, 150)
                audio.extend(interviewer.synthesize(turn["say"]))
                audio.extend(Audio.silence(24000, 150))
            ex = conv.exchange(audio, turn.get("after_ms", 800), tag=turn.get("tag"))
            b = ex.timing.barge_in
            if b is None:
                when = f"attend {ex.timing.wait_ms} ms"
            elif b.during == "onset":
                when = "coupe l'enfant pendant son hésitation, avant sa réponse"
            else:
                moment = "pendant une pause" if b.during == "pause" else "en pleine phrase"
                when = f"coupe l'enfant {moment}, après « {b.heard_text} »"
            print(f"[{i:02d}] Vous ({when}) > {ex.transcript.text}")
            if args.trainer:
                d = ex.result.decision
                print(f"      [formateur] {ex.result.classification.type} | {d.speech_act} | {d.reason}")
            print(f"     {child} > {render_plan(ex.result.speech_plan)}")
        log = session.end()
    except (VoiceError, ValueError, OSError) as e:
        print(e, file=sys.stderr)
        return 2
    conv.track.write_wav(out / "conversation.wav")
    (out / "conversation.json").write_text(json.dumps(
        [e.__dict__ for e in conv.events], ensure_ascii=False, indent=1), encoding="utf-8")
    tt = log.feedback.metrics.turn_taking
    if tt is not None:
        print(f"\nTours de parole : attente médiane {tt.median_wait_ms} ms ; interruptions {tt.interruptions or 'aucune'} ; "
              f"hésitations respectées {tt.hesitations_respected}/{tt.hesitations} ; "
              f"unités coupées {', '.join(tt.units_cut) or 'aucune'}")
    print(f"Audio : {out / 'conversation.wav'}  —  journal : {out / f'session_{log.session_id}.json'}")
    return 0


def export_cmd(args: argparse.Namespace) -> int:
    try:
        log = load_log(args.log)
    except ReplayError as e:
        print(e, file=sys.stderr)
        return 2
    out = Path(args.output or Path(args.log).with_suffix(".codage.csv"))
    export_for_coders(log, out)
    print(f"Transcription vierge pour codeurs : {out}")
    return 0


def check_cmd(args: argparse.Namespace) -> int:
    from nichd_sim.scenario_check import Level, check_scenario

    paths = args.paths or sorted(str(p) for p in Path("scenarios").glob("*.yaml"))
    errors = 0
    for path in paths:
        try:
            findings = check_scenario(load_scenario(path))
        except ScenarioError as e:
            print(e)
            errors += 1
            continue
        n_err = sum(f.level == Level.ERROR for f in findings)
        n_warn = sum(f.level == Level.WARNING for f in findings)
        print(f"{path} : {n_err} erreur(s), {n_warn} avertissement(s)")
        for f in findings:
            print(f"  - {f}")
        errors += n_err
    return 1 if errors else 0


def ui_cmd(args: argparse.Namespace) -> int:
    import subprocess

    app = Path(__file__).resolve().parent / "ui" / "app.py"
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app),
        "--server.port", str(args.port),
        # Local only by default: the simulator drives a local LLM and must not be exposed.
        "--server.address", args.host,
    ]
    if args.headless:
        cmd += ["--server.headless", "true"]
    return subprocess.call(cmd)


def eval_cmd(args: argparse.Namespace) -> int:
    from nichd_sim.evaluation import evaluate, load_scenarios, load_testset

    items = load_testset()
    if args.limit:
        items = items[: args.limit]
    clf = LLMClassifier(OllamaClient(args.model, args.ollama_url), think=parse_think(args.think))

    def progress(k, n, r):
        mark = "✓" if r.type_ok and (r.gold["target"] is None or r.target_ok) else "✗"
        print(f"\r[{k}/{n}] {mark} {r.id}", end="", flush=True)

    report = evaluate(clf, items, load_scenarios(args.scenarios_dir), model=f"{args.model} (réflexion : {args.think})",
                      skill_version=clf.skill_version, progress=progress)
    print()
    md = report.to_markdown()
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Rapport : {args.output}")
    print("\n".join(md.splitlines()[:9]))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nichd-sim", description="Simulateur d'audition NICHD")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("play", help="mener un entretien dans le terminal")
    p.add_argument("scenario", help="fichier de scénario YAML")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--classifier", default="manual", choices=["manual", "llm"])
    p.add_argument("--classifier-model", default=None, help="modèle Ollama du classifieur (défaut : --model)")
    p.add_argument("--classifier-think", default=DEFAULT_CLASSIFIER_THINK,
                   help="réflexion du classifieur : off, low, medium, high")
    p.add_argument("--realizer", default="template", choices=["template", "llm"])
    p.add_argument("--model", default=DEFAULT_MODEL, help="modèle Ollama")
    p.add_argument("--ollama-url", default=DEFAULT_URL)
    p.add_argument("--log-dir", default="sessions")
    p.add_argument("--trainer", action="store_true", help="mode formateur : affiche classification et décision")
    p.add_argument("--no-rephrase", action="store_true", help="pas de reformulations LLM dans le retour (hors ligne)")
    p.add_argument("--summary", action="store_true", help="rédiger une synthèse en fin d'entretien, confrontée aux faits")
    p.add_argument("--voice", metavar="DOSSIER", help="écrire la réponse de l'enfant en audio (un WAV par tour)")
    p.add_argument("--speaker", default=None,
                   help="voix : kokoro (enfant), kokoro-adulte, tone (sans modèle) ; défaut : kokoro si installé")
    p.set_defaults(func=play)

    a = sub.add_parser("render-audio", help="rendre en audio les réponses d'un journal de session (sans LLM)")
    a.add_argument("log", help="journal JSON de session")
    a.add_argument("-o", "--output", help="dossier de sortie (défaut : audio/<session>)")
    a.add_argument("--speaker", default=None,
                   help="voix : kokoro (enfant), kokoro-adulte, tone (sans modèle) ; défaut : kokoro si installé")
    a.set_defaults(func=render_audio_cmd)

    r = sub.add_parser("replay", help="rejouer une session depuis son journal, sans LLM")
    r.add_argument("log", help="journal JSON de session")
    r.add_argument("--scenario", help="fichier de scénario (sinon recherché par identifiant)")
    r.add_argument("--scenarios-dir", default="scenarios")
    r.set_defaults(func=replay_cmd)

    c = sub.add_parser("converse", help="conversation vocale scriptée (YAML) : transcription, session, voix")
    c.add_argument("script", help="script YAML (scenario, seed, turns: say|wav, after_ms, tag)")
    c.add_argument("-o", "--output", default="audio/conversation", help="dossier de sortie")
    c.add_argument("--classifier", default="manual", choices=["manual", "llm"])
    c.add_argument("--classifier-model", default=None)
    c.add_argument("--classifier-think", default=DEFAULT_CLASSIFIER_THINK)
    c.add_argument("--realizer", default="template", choices=["template", "llm"])
    c.add_argument("--model", default=DEFAULT_MODEL)
    c.add_argument("--ollama-url", default=DEFAULT_URL)
    c.add_argument("--speaker", default=None, help="voix de l'enfant (défaut : kokoro si installé)")
    c.add_argument("--seed", type=int, default=0, help="seed du réaliseur LLM")
    c.add_argument("--trainer", action="store_true")
    c.set_defaults(func=converse_cmd)

    w = sub.add_parser("transcribe", help="transcrire des enregistrements WAV (Whisper large-v3)")
    w.add_argument("wavs", nargs="+")
    w.set_defaults(func=transcribe_cmd)

    e = sub.add_parser("export", help="exporter une transcription vierge (CSV) pour des codeurs humains")
    e.add_argument("log", help="journal JSON de session")
    e.add_argument("-o", "--output", help="fichier CSV de sortie")
    e.set_defaults(func=export_cmd)

    k = sub.add_parser("check-scenario", help="vérifier des fiches de scénario (défaut : scenarios/*.yaml)")
    k.add_argument("paths", nargs="*")
    k.set_defaults(func=check_cmd)

    u = sub.add_parser("ui", help="lancer l'interface web (Streamlit)")
    u.add_argument("--port", type=int, default=8501)
    u.add_argument("--host", default="127.0.0.1", help="adresse d'écoute (défaut : locale uniquement)")
    u.add_argument("--headless", action="store_true")
    u.set_defaults(func=ui_cmd)

    v = sub.add_parser("eval-classifier", help="évaluer le classifieur LLM sur le jeu de test du skill")
    v.add_argument("--model", default=DEFAULT_MODEL)
    v.add_argument("--ollama-url", default=DEFAULT_URL)
    v.add_argument("--scenarios-dir", default="scenarios")
    v.add_argument("--limit", type=int, default=None)
    v.add_argument("--think", default=DEFAULT_CLASSIFIER_THINK, help="réflexion du classifieur : off, low, medium, high")
    v.add_argument("-o", "--output", help="rapport Markdown")
    v.set_defaults(func=eval_cmd)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
