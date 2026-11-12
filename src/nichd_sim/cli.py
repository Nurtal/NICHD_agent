"""Command-line interface: play a session in the terminal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nichd_sim.classifiers.manual import HELP, ManualClassificationError, ManualClassifier
from nichd_sim.realization import TemplateRealizer
from nichd_sim.scenario import ScenarioError, load_scenario
from nichd_sim.session import Session

COMMANDS = """Commandes : /aide  /unites  /etat  /fin"""


def build_classifier(name: str):
    if name == "manual":
        return ManualClassifier()
    raise SystemExit(f"classifieur inconnu : {name}")


def build_realizer(name: str):
    if name == "template":
        return TemplateRealizer()
    raise SystemExit(f"realizer inconnu : {name}")


def play(args: argparse.Namespace) -> int:
    try:
        scenario = load_scenario(args.scenario)
    except ScenarioError as e:
        print(e, file=sys.stderr)
        return 2
    session = Session(
        scenario,
        build_classifier(args.classifier),
        build_realizer(args.realizer),
        seed=args.seed,
        log_dir=args.log_dir,
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
        if args.trainer:
            c, d = result.classification, result.decision
            print(f"  [formateur] {c.type}{' → ' + c.target if c.target else ''} | {d.speech_act} | {d.reason}")
        print(f"{child} > {result.response}")
    session.end()
    if args.log_dir:
        print(f"Journal : {Path(args.log_dir) / f'session_{session.log.session_id}.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nichd-sim", description="Simulateur d'audition NICHD")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("play", help="mener un entretien dans le terminal")
    p.add_argument("scenario", help="fichier de scénario YAML")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--classifier", default="manual", choices=["manual"])
    p.add_argument("--realizer", default="template", choices=["template"])
    p.add_argument("--log-dir", default="sessions")
    p.add_argument("--trainer", action="store_true", help="mode formateur : affiche classification et décision")
    args = parser.parse_args(argv)
    return play(args)


if __name__ == "__main__":
    raise SystemExit(main())
