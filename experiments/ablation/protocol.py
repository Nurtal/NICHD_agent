"""Ablation: hybrid child (deterministic engine + LLM realization) vs. LLM-only child.

Shared material: scripted interviews, the LLM-only baseline prompt and the text detectors used to
score both conditions identically.

Each script line is a manual-classifier utterance (``[tag@phase:target=extra] text``): the hybrid
condition is driven by these gold labels (so the classifier is out of the comparison), the LLM-only
condition only sees the text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from nichd_sim.realization import REGISTERS
from nichd_sim.scenario import Scenario
from nichd_sim.text import mentions, normalize


@dataclass(frozen=True)
class Plan:
    neutral: str  # how the interviewer names the neutral event
    girl: bool
    directives: tuple[tuple[str, str], tuple[str, str], tuple[str, str]]  # (unit id, question) A, B, C
    out_of_scenario: tuple[str, str]  # directive questions about details absent from the sheet
    false_suggestions: tuple[tuple[str, tuple[str, ...]], tuple[str, tuple[str, ...]]]  # (question, keywords)


PLANS: dict[str, Plan] = {
    "s01_bagarre_parc": Plan(
        "ton dernier anniversaire", False,
        (("d_pousse", "Qui a poussé qui ?"), ("d_tombe", "Qu'est-ce qui est arrivé à Monsieur Bertin ?"),
         ("a_part", "Qu'est-ce qu'il a fait après, le monsieur au blouson rouge ?")),
        ("De quelle couleur était la voiture du monsieur ?", "Comment il s'appelait, le monsieur au blouson rouge ?"),
        (("Le monsieur avait un couteau, c'est ça ?", ("couteau",)),
         ("Il y avait une dame qui criait aussi, hein ?", ("dame",))),
    ),
    "s02_violences_maison": Plan(
        "la sortie à la piscine", True,
        (("d_karim", "Qui était avec toi à la maison ?"), ("b_cuisine", "Ça s'est passé dans quelle pièce ?"),
         ("a_bleu", "Qu'est-ce que tu avais sur le bras après ?")),
        ("De quelle couleur était son pull ?", "Quel âge il a ?"),
        (("Il t'a enfermée dans le placard, c'est ça ?", ("placard",)),
         ("C'était le matin avant l'école, hein ?", ("matin",))),
    ),
    "s03_vol_boulangerie": Plan(
        "le match de foot", False,
        (("d_vol", "Qu'est-ce que la dame a fait ?"), ("d_dame", "Comment elle était, la dame ?"),
         ("a_velo", "Comment elle est partie ?")),
        ("Combien d'argent il y avait dans le portefeuille ?", "Comment s'appelait la boulangère ?"),
        (("La dame avait un couteau, c'est ça ?", ("couteau",)),
         ("Elle est partie en voiture, hein ?", ("voiture",))),
    ),
    "s04_violences_conjugales": Plan(
        "la kermesse", True,
        (("d_dispute", "Qui se disputait ?"), ("d_mur", "Qu'est-ce que papa a fait à maman ?"),
         ("a_voisine", "Qui est venu après ?")),
        ("Quelle heure il était exactement ?", "Comment s'appelle le chien des voisins ?"),
        (("Papa avait bu de l'alcool, c'est ça ?", ("alcool", "avait bu")),
         ("Il a cassé la télé, hein ?", ("tele",))),
    ),
    "s05_negligence": Plan(
        "la sortie au zoo", False,
        (("b_seul", "Qu'est-ce qui se passe quand maman s'en va le soir ?"), ("d_jade", "Qui est avec toi à la maison ?"),
         ("a_retour", "Quand est-ce que maman rentre ?")),
        ("Où elle va, maman, le soir ?", "Comment s'appelle ta maîtresse ?"),
        (("Maman t'a laissé tout seul pendant trois jours, c'est ça ?", ("trois jours",)),
         ("Elle ferme la porte à clé pour que tu sortes pas, hein ?", ("cle",))),
    ),
    "s06_racket": Plan(
        "le spectacle", True,
        (("d_argent", "Qu'est-ce qu'ils t'ont demandé ?"), ("d_collegiens", "C'était qui ?"),
         ("a_mere", "À qui tu l'as raconté ?")),
        ("Comment s'appelait le grand avec la casquette ?", "Quelle marque de baskets ils avaient ?"),
        (("Ils avaient un couteau, c'est ça ?", ("couteau",)),
         ("Ils t'ont poussée par terre, hein ?", ("par terre",))),
    ),
    "s07_delit_fuite": Plan(
        "la séance de cinéma", False,
        (("d_feu", "Qu'est-ce qu'elle a fait, la voiture, au carrefour ?"), ("d_cycliste", "Qui traversait ?"),
         ("a_fuite", "Où elle est partie, la voiture ?")),
        ("Quelle était la marque de la voiture ?", "Combien de personnes il y avait sur le trottoir ?"),
        (("C'était un camion, hein ?", ("camion",)),
         ("Le cycliste saignait beaucoup, c'est ça ?", ("saign",))),
    ),
}

# Turn roles, used by the analysis (1-based turn index → role).
ROLES = {
    1: "rapport", 2: "rapport", 3: "rule", 4: "rule", 5: "practice", 6: "practice", 7: "practice",
    8: "transition", 9: "invitation", 10: "facilitator", 11: "invitation",
    12: "dir_A", 13: "dir_B", 14: "out_1", 15: "sug_1", 16: "dir_C", 17: "out_2", 18: "sug_2",
    19: "dir_A_repeat", 20: "recall", 21: "invitation_late", 22: "closure", 23: "closure",
}


def script(scenario: Scenario) -> list[str]:
    p = PLANS[scenario.id]
    name, e = scenario.child_profile.name, ("e" if p.girl else "")
    (a, qa), (b, qb), (c, qc) = p.directives
    (s1, _), (s2, _) = p.false_suggestions
    return [
        f"[soutien@rapport] Bonjour {name}, je m'appelle Claire. Mon travail, c'est d'écouter les enfants.",
        "[inv@rapport] Qu'est-ce que tu aimes faire après l'école ?",
        "[regle@regles] Si je te pose une question et que tu ne sais pas la réponse, tu peux me dire « je sais pas ».",
        "[regle@regles] Et si je me trompe, tu peux me dire que je me trompe.",
        f"[inv@pratique] Raconte-moi tout sur {p.neutral}, du début à la fin.",
        "[inv@pratique] Et puis, qu'est-ce qui s'est passé ?",
        f"[inv@pratique] Raconte-moi encore plus sur {p.neutral}.",
        f"[inv@transition] Maintenant, dis-moi pourquoi tu es venu{e} me parler aujourd'hui.",
        "[inv@faits] Raconte-moi tout ce qui s'est passé, du début à la fin.",
        "[fac@faits] Et puis ?",
        "[inv@faits] Et ensuite, qu'est-ce qui s'est passé ?",
        f"[dir:{a}] {qa}",
        f"[dir:{b}] {qb}",
        f"[dir:hors] {p.out_of_scenario[0]}",
        f"[sug:hors={_prop(s1)}] {s1}",
        f"[dir:{c}] {qc}",
        f"[dir:hors] {p.out_of_scenario[1]}",
        f"[sug:hors={_prop(s2)}] {s2}",
        f"[dir:{a}] {qa}",
        "[inv@faits] Raconte-moi encore une fois tout ce qui s'est passé, depuis le début.",
        "[inv@faits] Est-ce qu'il y a autre chose que je devrais savoir ?",
        "[inv@cloture] Est-ce qu'il y a autre chose que tu veux me dire ?",
        f"[soutien@cloture] Merci {name}, tu m'as bien aidé{e}.",
    ]


def _prop(question: str) -> str:
    return re.sub(r",? (c'est ça|hein) \?$", "", question).strip()


def strip_tag(utterance: str) -> str:
    return re.sub(r"^\s*\[[^\]]*\]\s*", "", utterance)


# -- LLM-only baseline ----------------------------------------------------------------


def _level(x: float) -> str:
    return "très faible" if x < 0.2 else "faible" if x < 0.4 else "moyenne" if x < 0.6 else "forte" if x < 0.8 else "très forte"


def baseline_system_prompt(scenario: Scenario) -> str:
    """A strong LLM-only child: same model, the whole sheet, the profile and its intended effects."""
    prof = scenario.child_profile
    facts = "\n".join(f"- {u.value}" for _, u in scenario.target_units())
    neutral = "\n".join(f"- {u.value}" for _, u in scenario.neutral_units())
    return (
        f"Tu joues le rôle de {prof.name}, {prof.age} ans, entendu(e) par un(e) professionnel(le) lors d'une "
        f"audition d'enfant (protocole NICHD). Contexte : {scenario.intake_context.strip()}\n\n"
        f"Ce qui s'est réellement passé (tes souvenirs, à ne révéler que progressivement) :\n{facts}\n\n"
        f"Un autre souvenir, sans rapport (utile si on te demande de raconter autre chose) :\n{neutral}\n\n"
        f"Ton profil : réticence à parler {_level(prof.reluctance)} ({prof.reluctance}), compétences verbales "
        f"{_level(prof.verbal_skills)} ({prof.verbal_skills}), suggestibilité {_level(prof.suggestibility)} "
        f"({prof.suggestibility}).\n\n"
        "Comporte-toi comme un vrai enfant de cet âge avec ce profil :\n"
        "- tu ne parles de l'événement que si on t'y invite, et d'autant plus difficilement que tu es réticent ;\n"
        "- face à une question ouverte tu racontes quelques éléments ; face à une question précise tu ne réponds "
        "qu'à cette question ;\n"
        "- si on te demande quelque chose qui n'est pas dans tes souvenirs, tu dis en général que tu ne sais pas ;\n"
        "- face à une suggestion fausse, un enfant suggestible peut dire oui et la reprendre ensuite ;\n"
        "- tu restes non explicite : jamais de détail cru ou violent ;\n"
        f"- {REGISTERS[prof.age_band].format(age=prof.age)}\n"
        "Réponds uniquement par ce que dit l'enfant, en une à trois phrases."
    )


def expected_acceptance(scenario: Scenario) -> float:
    """Acceptance rate of a false suggestion the hybrid engine targets for this profile (after 2 ground rules)."""
    from nichd_sim.parameters import Parameters

    params = Parameters.load(scenario.child_profile.age_band, scenario.parameter_overrides)
    lo, hi = params["suggestibility_multiplier_range"]
    acq = max(0.0, scenario.child_profile.suggestibility - 2 * params["ground_rule_acquiescence_drop"])
    return min(1.0, params["p_acquiesce"] * (lo + (hi - lo) * acq))


# Few-shot examples on a fictional case unrelated to the 7 scenarios.
_EXAMPLES = """Exemples de comportement attendu (autre enfant, autre histoire : un vol de goûter à la cantine) :
- Adulte : « Qu'est-ce que tu aimes faire le mercredi ? » → Enfant : « Je joue aux billes. » (rien sur l'événement)
- Adulte : « Tu peux me dire si je me trompe. » → Enfant : « D'accord. »
- Adulte : « Raconte-moi ta sortie au cirque. » → Enfant : « Y avait des clowns. Et un éléphant. » (seulement le souvenir demandé)
- Adulte : « Qui a pris ton goûter ? » → Enfant : « C'est Hugo. » (seulement ce qui est demandé)
- Adulte : « Il avait un sac rouge, hein ? » (faux) → Enfant suggestible : « Oui, un sac rouge. » ; enfant peu suggestible : « Non. »
- Adulte : « Raconte encore tout. » → l'enfant suggestible qui avait dit oui reprend parfois le sac rouge comme un vrai souvenir."""

_REMINDER = ("(Rappel : tu ne parles de l'événement que si l'adulte t'invite à en parler ; tu réponds seulement à "
             "ce qui est demandé ; tu es {name}, {age} ans ; tu acceptes environ {pct} % des suggestions fausses.)")


def baseline_messages(scenario: Scenario, history: list[tuple[str, str]], current: str, strong: bool = False) -> list[dict]:
    lines = [f"{'Adulte' if s == 'interviewer' else 'Toi'} : {t}" for s, t in history]
    system = baseline_system_prompt(scenario)
    reminder = ""
    if strong:
        pct = round(100 * expected_acceptance(scenario))
        system += (f"\n\nTa suggestibilité correspond à environ {pct} % de suggestions fausses acceptées : quand l'adulte "
                   "suggère quelque chose de faux, il t'arrive de dire oui, puis de le répéter plus tard comme un vrai "
                   f"souvenir.\n\n{_EXAMPLES}")
        prof = scenario.child_profile
        reminder = "\n" + _REMINDER.format(name=prof.name, age=prof.age, pct=pct)
    user = (f"Conversation depuis le début :\n" + "\n".join(lines) + "\n\n" if lines else "") + (
        f"L'adulte te dit maintenant : « {current} »{reminder}\nTa réponse :"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# -- detectors (identical for both conditions) ------------------------------------------

_DK = re.compile(
    r"\b(sais pas|sais plus|sait pas|souviens (pas|plus)|rappelle (pas|plus)|aucune idee|pas fait attention|"
    r"pas vu|pas remarque|connais pas|pas regarde|j'?sais pas|ne sais|je ne me souviens)\b"
)


def units_mentioned(scenario: Scenario, text: str, central_only: bool = False) -> set[str]:
    """Target facts whose anchors appear in the text. Anchors that also occur in the neutral
    event (e.g. "bleu" in "bonnet de bain bleu") are ignored to avoid false positives."""
    norm = normalize(text)
    neutral = normalize(" ".join(u.value for _, u in scenario.neutral_units()))
    return {
        u.id for _, u in scenario.target_units()
        if (not central_only or u.centrality.value == "central")
        and any(mentions(norm, a) and not mentions(neutral, a) for a in u.anchors)
    }


def is_dont_know(text: str) -> bool:
    return bool(_DK.search(normalize(text)))


def is_yes(text: str) -> bool:
    head = normalize(text).split()[:4]
    return "oui" in head and "non" not in head


_NEG = re.compile(r"\b(non|pas|jamais|rien|faux|trompes?|trompez)\b")


def accepts_suggestion(text: str, keywords: tuple[str, ...]) -> bool:
    """Says yes, or takes up the suggested detail without any negation."""
    norm = normalize(text)
    if _NEG.search(norm):
        return is_yes(text) and not normalize(text).split()[:1] == ["non"] and "pas" not in norm.split()[:6]
    return is_yes(text) or has_keyword(text, keywords)


def has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    norm = normalize(text)
    return any(mentions(norm, k) for k in keywords)
