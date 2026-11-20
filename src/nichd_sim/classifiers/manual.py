"""Manual classifier: the interviewer tags each utterance with its NICHD type.

Syntax: `[tag] text`, `[tag:target] text`, optionally `[tag@phase...]`, e.g. `[dir:p_pousse] Qui a poussé ?`.
Flags after the tag (skill 0.3.0 fields): `[inv+fin]`, `[choix+sais:unit=prop]`, `[regle+promesse]`, see FLAGS.
`target` is an info unit id, or `hors` for out-of-scenario. For suggestive
questions: `[sug:unit=proposition]`. For option-posing: `[choix:unit=opt1|opt2]`, or
`[choix:unit=proposition]` for a yes/no question.
"""

from __future__ import annotations

import re

from nichd_sim.classification import OUT_OF_SCENARIO, Classification, ClassificationContext, QuestionType


class ManualClassificationError(ValueError):
    pass


TAGS: dict[str, QuestionType] = {
    "inv": QuestionType.INVITATION,
    "ind": QuestionType.CUED_INVITATION,
    "dir": QuestionType.DIRECTIVE,
    "choix": QuestionType.OPTION_POSING,
    "sug": QuestionType.SUGGESTIVE,
    "fac": QuestionType.FACILITATOR,
    "regle": QuestionType.GROUND_RULE,
    "soutien": QuestionType.SUPPORT,
    "comp": QuestionType.COMPOUND,
    "autre": QuestionType.OTHER,
}

HELP = """Préfixez chaque énoncé par son type :
  [inv]              invitation             [fac]      facilitateur
  [ind:unité]        invitation indicée     [regle]    énoncé de règle
  [dir:unité|hors]   question directive     [soutien]  soutien / rapport
  [choix:unité=a|b]  question à choix       [autre]    autre
  [choix:unité=prop] question oui/non
  [sug:unité=prop]   question suggestive    [comp:unité] question composée
Drapeaux (après le type) : +debut +pendant +fin (segment), +sais (« tu te souviens… ? »), +pourquoi,
  +jsp +comprends +corrige +absent +verite +promesse +entrainement (règles), +episodique +generique (pratique)."""

PHASES = {
    "rapport": "rapport",
    "regles": "ground_rules",
    "pratique": "narrative_practice",
    "transition": "transition",
    "faits": "substantive",
    "cloture": "closure",
}

FLAGS: dict[str, tuple[str, object]] = {
    "debut": ("segment", "before"), "avant": ("segment", "before"), "pendant": ("segment", "during"),
    "fin": ("segment", "after"), "apres": ("segment", "after"),
    "sais": ("knowledge_question", True), "pourquoi": ("causal", True),
    "episodique": ("practice_kind", "episodic"), "generique": ("practice_kind", "generic"),
    "jsp": ("ground_rule_kind", "dont_know"), "comprends": ("ground_rule_kind", "dont_understand"),
    "corrige": ("ground_rule_kind", "correct_me"), "absent": ("ground_rule_kind", "not_there"),
    "verite": ("ground_rule_kind", "truth"), "promesse": ("ground_rule_kind", "promise"),
    "entrainement": ("ground_rule_kind", "practice"),
}

_PATTERN = re.compile(
    r"^\s*\[(?P<tag>[a-z]+)(?P<flags>(?:\+[a-z]+)*)(?:@(?P<phase>[a-z]+))?(?::(?P<target>[^\]=]+)(?:=(?P<extra>[^\]]*))?)?\]\s*(?P<text>.*)$",
    re.S,
)


class ManualClassifier:
    def classify(self, utterance: str, context: ClassificationContext) -> Classification:
        m = _PATTERN.match(utterance)
        if not m or m["tag"] not in TAGS:
            raise ManualClassificationError(HELP)
        qtype = TAGS[m["tag"]]
        if m["phase"] and m["phase"] not in PHASES:
            raise ManualClassificationError(f"Phase inconnue : {m['phase']!r} ({', '.join(PHASES)})")
        target = m["target"].strip() if m["target"] else None
        if target == "hors":
            target = OUT_OF_SCENARIO
        if target and target != OUT_OF_SCENARIO and context.scenario.unit(target) is None:
            raise ManualClassificationError(f"Unité inconnue : {target!r} (tapez /unites pour la liste)")
        extra = m["extra"]
        fields: dict[str, object] = {}
        for flag in filter(None, (m["flags"] or "").split("+")):
            if flag not in FLAGS:
                raise ManualClassificationError(f"Drapeau inconnu : {flag!r} ({', '.join(FLAGS)})")
            name, value = FLAGS[flag]
            fields[name] = value
        return Classification(
            **fields,
            type=qtype,
            target=target,
            suggested_proposition=extra if extra and (
                qtype == QuestionType.SUGGESTIVE or (qtype == QuestionType.OPTION_POSING and "|" not in extra)
            ) else None,
            options=extra.split("|") if extra and "|" in extra and qtype == QuestionType.OPTION_POSING else None,
            phase_hints=[PHASES[m["phase"]]] if m["phase"] else [],
            clean_text=m["text"].strip(),
        )


def strip_tag(utterance: str) -> str:
    """The utterance without its manual tag (what the child 'hears')."""
    m = _PATTERN.match(utterance)
    return m["text"].strip() if m else utterance
