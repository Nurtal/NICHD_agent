"""Complete NICHD skill and classifier evaluation (#8)."""

from collections import Counter

import pytest

from doubles import ROOT
from nichd_sim.classification import OUT_OF_SCENARIO, Classification, QuestionType
from nichd_sim.classifiers.llm import Skill
from nichd_sim.evaluation import cohen_kappa, evaluate, load_scenarios, load_testset
from nichd_sim.text import normalize

SCENARIOS = load_scenarios(ROOT / "scenarios")


def test_testset_and_fewshot_examples_are_strictly_disjoint():
    fewshot = {normalize(e["utterance"]) for e in Skill.load().examples}
    test = [normalize(t["utterance"]) for t in load_testset()]
    assert not fewshot & set(test)
    assert len(test) == len(set(test)), "duplicate utterance in the test set"


def test_skill_has_about_150_annotated_utterances_covering_types_and_phases():
    examples, test = Skill.load().examples, load_testset()
    assert len(examples) + len(test) >= 140
    types = Counter(t["label"]["type"] for t in test)
    assert set(types) == {q.value for q in QuestionType}
    phases = {t["label"]["phase_hint"] for t in test}
    assert phases == {"rapport", "ground_rules", "narrative_practice", "transition", "substantive", "closure"}
    assert sum(t.get("ambiguous", False) for t in test) >= 8


@pytest.mark.parametrize("item", load_testset(), ids=lambda t: t["id"])
def test_testset_labels_are_consistent_with_their_scenario(item):
    sc = SCENARIOS[item["scenario"]]
    lab = item["label"]
    assert set(lab) == set(Skill.load().schema["required"])
    for uid in item["already_said"]:
        assert sc.unit(uid) is not None, uid
    if lab["target"] not in (None, OUT_OF_SCENARIO):
        assert sc.unit(lab["target"]) is not None, lab["target"]
    targeted = {"cued_invitation", "directive", "option_posing", "suggestive", "compound"}
    assert (lab["target"] is not None) == (lab["type"] in targeted)
    assert (lab["inner_type"] is not None) == (lab["type"] == "compound")
    if lab["type"] == "suggestive":
        assert lab["suggested_proposition"]


def test_cohen_kappa():
    assert cohen_kappa(list("aabb"), list("aabb")) == 1.0
    assert cohen_kappa(list("aabb"), list("abab")) == pytest.approx(0.0)
    # classic example: 20 items, p_o = 0.7, p_e = 0.5 → κ = 0.4
    gold = ["y"] * 10 + ["n"] * 10
    pred = ["y"] * 7 + ["n"] * 3 + ["y"] * 3 + ["n"] * 7
    assert cohen_kappa(gold, pred) == pytest.approx(0.4)


class OracleClassifier:
    """Answers with the gold label, except for a chosen set of items."""

    def __init__(self, items, wrong=()):
        self.by_utt = {i["utterance"]: i for i in items}
        self.wrong = set(wrong)
        self.skill_version = "test"

    def classify(self, utterance, context):
        item = self.by_utt[utterance]
        lab = item["label"]
        if item["id"] in self.wrong:
            return Classification(type=QuestionType.OTHER)
        return Classification(
            type=QuestionType(lab["type"]),
            target=lab["target"],
            inner_type=QuestionType(lab["inner_type"]) if lab["inner_type"] else None,
            phase_hints=[lab["phase_hint"]],
        )


def test_evaluation_report_with_an_oracle_and_with_errors():
    items = load_testset()
    perfect = evaluate(OracleClassifier(items), items, SCENARIOS, model="oracle", skill_version="t")
    assert perfect.kappa == pytest.approx(1.0) and perfect.target_accuracy == 1.0 and perfect.phase_accuracy == 1.0

    wrong = [i["id"] for i in items if i["label"]["type"] == "directive"][:4]
    report = evaluate(OracleClassifier(items, wrong), items, SCENARIOS, model="oracle", skill_version="t")
    assert report.kappa < 1.0
    assert report.confusion()[("directive", "other")] == 4
    md = report.to_markdown()
    assert "Kappa de Cohen" in md and "directive → other : 4" in md
    for wid in wrong:
        assert f"| {wid} |" in md
