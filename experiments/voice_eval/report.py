"""Builds docs/evaluations/voix.md from the raw results (results/*.json).

    uv run python experiments/voice_eval/report.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from checks import RESULTS, Check

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "evaluations" / "voix.md"

LEVELS = [
    ("n2", "N2 — Plausibilité du comportement simulé",
     "≈ 3 000 réponses simulées (8 scénarios + 2 variantes de s08, 10 seeds, 3 styles d'interviewer), puis 802 "
     "**paires contrôlées mensonge/vérité** : même session, même question sur le même fait protégé, seule la volonté "
     "de cacher change."),
    ("n0", "N0 — Fidélité du rendu : l'audio fait-il ce que la décision demande ?",
     "456 réponses rendues avec Kokoro (échantillon stratifié par niveau d'hésitation) : leur plan d'élocution "
     "sert de vérité terrain. On y ajoute des rendus contrôlés (mêmes textes à plusieurs débits et volumes). "
     "Segmentation par énergie, audibilité jugée par Whisper large-v3, « euh » contrôlés par pYIN."),
    ("n1auto", "N1-auto — Indicateurs objectifs de fluidité (proxy de la perception)",
     "Indicateurs connus pour prédire la fluidité perçue (Cucchiarini, Strik & Boves, 2002, *JASA* 111(6)), "
     "mesurés dans la réponse (silence initial exclu) sur les réponses d'au moins 8 mots, où des pauses internes "
     "sont possibles. **Proxy, pas preuve perceptive.**"),
    ("n1", "N1 — Test d'écoute à l'aveugle",
     "Lot préparé (`experiments/voice_eval/listening/`), **pas encore lancé** : aucun auditeur pour l'instant."),
    ("n4", "N4 — Tours de parole et interruptions",
     "≈ 430 échanges à vérité terrain connue (silence de tête exact, voix adulte Kokoro), `after_ms` tiré dans "
     "[−6 s ; +3 s], sans bruit et avec bruit blanc à 20, 10 et 5 dB de rapport signal sur bruit."),
    ("n3_stt", "N3 — Transcription de l'interviewer (pilote synthétique)",
     "Les 104 énoncés du jeu de test du skill, dits par 3 pseudo-locuteurs tirés de la seule voix française de "
     "Kokoro (hauteur et débit variés). **Optimiste** : de vraies voix seront plus difficiles."),
    ("n3_classifier", "N3 — Ce que la transcription coûte au classifieur",
     "Même classifieur et mêmes réglages qu'en production (LLM, réflexion par défaut), sur le texte d'origine puis "
     "sur les transcriptions."),
    ("cost", "Coût (rapporté seulement)", "Latences mesurées sur la station (2 × TITAN RTX), sans autre charge GPU."),
]

FINDINGS = """## Ce que l'évaluation a trouvé et corrigé

1. **Mensonge trahi par une réponse rapide (N2).** Un mensonge hésitait *moins* que la vérité sur le même fait
   (AUC 0,22). En cause, deux asymétries : la charge émotionnelle et la charge de récupération en mémoire venaient
   des faits *dits*. La version de couverture « je suis tombée dans l'escalier » n'en avait donc presque pas, alors
   que l'enfant parle du même événement douloureux. **Correction** : un mensonge porte la charge émotionnelle et de
   récupération du fait qu'il cache. Le poids du mensonge est ensuite **calibré sur les paires contrôlées** :
   - le poids initial de 0,5 donnait d ≈ 1,2 et une AUC de 0,81, soit un faux indice dans l'autre sens ;
   - le nouveau poids de 0,15 donne d ≈ 0,38 et une AUC de 0,61, l'ordre de grandeur des méta-analyses
     (Sporer & Schwandt, 2006).
2. **« euh » trop courts (N0).** 8 % des « euh » rendus par Kokoro duraient moins de 250 ms (jusqu'à 130 ms), plus
   proches d'un accroc que d'une hésitation. **Correction** : le worker Kokoro étire tout « euh » de moins de
   300 ms à environ 380 ms, hauteur conservée. 99,7 % passent désormais.
3. **Bruit pris pour de la parole (N4).** À 10 dB de rapport signal sur bruit, la détection par énergie prenait
   le bruit pour une prise de parole dès la première trame (erreur de 349 ms). **Correction** dans
   `Audio.voiced_bounds` : seuil relatif au niveau de bruit, plusieurs trames fortes consécutives exigées, et
   hystérésis pour les attaques douces. L'erreur tombe à 15 ms.
4. **Mesures elles-mêmes vérifiées.**
   - N0 : sur une vérité parfaite (voix `tone`), la segmentation retrouve tous les silences, à 4 ms près ; une
     diction cassée fait chuter le rappel des silences à 0,34.
   - N1 : des auditeurs simulés attentifs passent les contrôles, des auditeurs au hasard échouent.
   - N1 : le contrôle « mensonge au hasard » n'est valide que si les mêmes auditeurs perçoivent l'hésitation,
     car des auditeurs inattentifs sont eux aussi au hasard.
"""

LIMITS = """## Limites

- **Pas encore de perception humaine.** N1-auto est un proxy. Le test d'écoute (78 extraits, environ 30 minutes
  par auditeur) est prêt mais n'a pas été passé.
- **Transcription mesurée sur voix synthétique.** Les résultats sont optimistes. Les énoncés très courts (relances
  NICHD : « Et après ? », « Hmm hmm ») sont le point faible, en partie parce que Kokoro dit mal « hmm ».
- **Une seule voix française** dans Kokoro (`ff_siwis`). La voix d'enfant en est dérivée (hauteur et formants × 1,25).
- **Paramètres estimés.** Le poids du mensonge est calibré sur un ordre de grandeur de la littérature (adultes,
  méta-analyses), pas sur des données d'enfants en audition.
"""

RERUN = """## Rejouer

```bash
uv run python experiments/voice_eval/n2_plausibility.py         # N2 (sans audio, ~1 min)
uv run python experiments/voice_eval/make_corpus.py             # corpus N0 (Kokoro, ~1 min)
experiments/voice_eval/run_voice_env.sh n0_fidelity.py          # N0 + N1-auto (~2 min)
experiments/voice_eval/run_voice_env.sh n0_sanity.py            # contrôle des mesures N0
uv run python experiments/voice_eval/n4_turn_taking.py          # N4 (~5 min)
uv run python experiments/voice_eval/n3_stt.py                  # N3 transcription (~5 min)
uv run python experiments/voice_eval/n3_classifier.py           # N3 classifieur (~2 h, LLM)
uv run python experiments/voice_eval/cost.py                    # coût
uv run python experiments/voice_eval/report.py                  # ce rapport
```
"""


def load(level: str) -> list[Check] | None:
    path = RESULTS / f"{level}.json"
    if not path.exists():
        return None
    return [Check(**c) for c in json.loads(path.read_text(encoding="utf-8"))["checks"]]


def main() -> None:
    summary = ["| Niveau | Contrôles réussis | Échecs | Rapportés |", "|---|---|---|---|"]
    sections = []
    for level, title, method in LEVELS:
        checks = load(level)
        sections += [f"## {title}", "", method, ""]
        if checks is None:
            sections += ["*Pas encore de résultats.*", ""]
            summary.append(f"| {title.split(' —')[0]} | — | — | non lancé |")
            continue
        ok = sum(c.ok is True for c in checks)
        ko = sum(c.ok is False for c in checks)
        info = sum(c.ok is None for c in checks)
        summary.append(f"| {title.split(' —')[0]} | {ok} | {ko} | {info} |")
        sections += ["| Métrique | Valeur | Cible | | Note |", "|---|---|---|---|---|", *[c.row() for c in checks], ""]
    text = "\n".join([
        "# Évaluation de la chaîne vocale (diction, mensonge, voix, transcription)", "",
        f"*Généré par `experiments/voice_eval/report.py` le {date.today().isoformat()} à partir de "
        "`experiments/voice_eval/results/`. Plan et seuils fixés avant les mesures ; voir aussi "
        "[ADR 0002](../adr/0002-mensonge-diction-voix.md).*", "",
        "## Synthèse", "", *summary, "", FINDINGS, *sections, LIMITS, RERUN,
    ])
    OUT.write_text(text, encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
