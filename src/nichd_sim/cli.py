"""Command-line interface: play a session in the terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nichd_sim.classifiers.llm import LLMClassifier
from nichd_sim.classifiers.manual import HELP, ManualClassificationError, ManualClassifier
from nichd_sim.feedback import LLMRephraser, render_text
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
        return LLMClassifier(OllamaClient(args.classifier_model or args.model, args.ollama_url))
    raise SystemExit(f"classifieur inconnu : {args.classifier}")


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
    )
    child = scenario.child_profile.name
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
            for v in result.violations:
                print(f"  [formateur] ⚠ {VIOLATION_LABELS[v.kind]} : {v.phase}{' — ' + v.detail if v.detail else ''}")
            if c.suggested_proposition:
                print(f"  [formateur] proposition suggérée : {c.suggested_proposition}")
            if "error" in c.meta:
                print(f"  [formateur] classification en repli : {c.meta['error']}")
            for i, a in enumerate(turn.attempts):
                if not a.ok:
                    print(f"  [filtre] essai {i + 1} rejeté : {a.forbidden_terms + a.leaked_units + ['manque:' + m for m in a.missing_units] + (['vide'] if a.empty else [])} — {a.text!r}")
            if turn.fallback_used:
                print("  [filtre] réponse de repli utilisée")
        print(f"{child} > {result.response}")
        for notice in result.notices:
            print(f"  ⓘ {notice}")
    log = session.end()
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nichd-sim", description="Simulateur d'audition NICHD")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("play", help="mener un entretien dans le terminal")
    p.add_argument("scenario", help="fichier de scénario YAML")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--classifier", default="manual", choices=["manual", "llm"])
    p.add_argument("--classifier-model", default=None, help="modèle Ollama du classifieur (défaut : --model)")
    p.add_argument("--realizer", default="template", choices=["template", "llm"])
    p.add_argument("--model", default=DEFAULT_MODEL, help="modèle Ollama")
    p.add_argument("--ollama-url", default=DEFAULT_URL)
    p.add_argument("--log-dir", default="sessions")
    p.add_argument("--trainer", action="store_true", help="mode formateur : affiche classification et décision")
    p.add_argument("--no-rephrase", action="store_true", help="pas de reformulations LLM dans le retour (hors ligne)")
    p.set_defaults(func=play)

    r = sub.add_parser("replay", help="rejouer une session depuis son journal, sans LLM")
    r.add_argument("log", help="journal JSON de session")
    r.add_argument("--scenario", help="fichier de scénario (sinon recherché par identifiant)")
    r.add_argument("--scenarios-dir", default="scenarios")
    r.set_defaults(func=replay_cmd)

    e = sub.add_parser("export", help="exporter une transcription vierge (CSV) pour des codeurs humains")
    e.add_argument("log", help="journal JSON de session")
    e.add_argument("-o", "--output", help="fichier CSV de sortie")
    e.set_defaults(func=export_cmd)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
