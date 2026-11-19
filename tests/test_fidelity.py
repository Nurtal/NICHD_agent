"""The fidelity harness (experiments/fidelity/run.py) runs and reports every probe."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _harness():
    spec = importlib.util.spec_from_file_location("fidelity_run", ROOT / "experiments" / "fidelity" / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up
    spec.loader.exec_module(module)
    return module


def test_every_probe_runs_and_the_report_lists_it():
    run = _harness()
    results = [probe(range(5)) for probe in run.PROBES]
    text = run.report(results, 5)
    for r in results:
        assert r.piste and r.valeurs and f"| {r.piste} |" in text
