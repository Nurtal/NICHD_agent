"""Live check in two passes, one model loaded at a time (shared GPUs).

pass 1: LLM classifier (qwen3.8, think medium) + template realizer -> classifications
pass 2: same session, logged classifications + LLM realizer (gemma4:31b) -> child's words
Decisions are identical in both passes (same classifications, same seed)."""
import json, sys
from pathlib import Path
from nichd_sim.classification import Classification
from nichd_sim.classifiers.llm import LLMClassifier
from nichd_sim.llm import OllamaClient
from nichd_sim.realization import LLMRealizer, TemplateRealizer
from nichd_sim.scenario import load_scenario
from nichd_sim.session import Session

mode, scen, script, seed, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), Path(sys.argv[5])
sc = load_scenario(scen)
lines = [l.strip() for l in Path(script).read_text(encoding="utf-8").splitlines() if l.strip()]
cache = out.with_suffix(".classif.json")

class Cached:
    def __init__(self): self.items = [Classification.model_validate(c) for c in json.loads(cache.read_text())]
    def classify(self, u, ctx): return self.items.pop(0)

def unload(model):
    import urllib.request
    req = urllib.request.Request("http://127.0.0.1:11434/api/generate",
                                 data=json.dumps({"model": model, "keep_alive": 0}).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()

if mode == "classify":
    clf = LLMClassifier(OllamaClient("qwen3.8:latest", keep_alive="5m", timeout=300), think="medium")
    s = Session(sc, clf, TemplateRealizer(), seed=seed)
    for u in lines:
        s.turn(u)
    log = s.end()
    cache.write_text(json.dumps([t.classification.model_dump(mode="json") for t in log.turns], ensure_ascii=False))
    unload("qwen3.8:latest")
else:
    s = Session(sc, Cached(), LLMRealizer(OllamaClient("gemma4:31b", keep_alive="5m", timeout=300), seed=seed), seed=seed)
    rows = []
    for u in lines:
        r = s.turn(u)
        d = r.decision
        rows.append(f"**Q :** {u}  \n`{d.effective_type} → {d.speech_act}` {d.reason}  \n**Enfant :** {r.response}"
                    + ("  *(repli)*" if r.fallback_used else ""))
    log = s.end()
    out.write_text(log.model_dump_json(indent=2), encoding="utf-8")
    out.with_suffix(".md").write_text("\n\n".join(rows) + "\n", encoding="utf-8")
    unload("gemma4:31b")
