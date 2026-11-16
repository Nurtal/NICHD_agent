# Ablation : enfant hybride vs enfant 100 % LLM

*13 novembre 2026. Code : `experiments/ablation/` (protocole, exécution, analyse). Transcriptions brutes : `experiments/ablation/results/transcripts.jsonl`. Tableaux générés : `experiments/ablation/results/report.md`.*

## Question

Le découplage « moteur de comportement déterministe + LLM limité à la mise en mots » apporte-t-il quelque chose par rapport à un enfant simulé entièrement par le LLM, à qui l'on donne toute la fiche du scénario et des consignes de comportement ?

## Dispositif

- **Même modèle** pour les deux conditions : `qwen3.8:latest` (local, Ollama), température 0,7, sans réflexion.
- **Mêmes entretiens scriptés** : 23 tours identiques par scénario (rapport, règles de base, pratique narrative, transition, invitations, 3 questions directives dont une répétée, 2 questions sur des détails absents de la fiche, 2 suggestions fausses, rappel libre, clôture). 7 scénarios × 3 graines = **21 entretiens par condition**, 966 réponses.
- **Hybride** : notre simulateur, piloté par les étiquettes NICHD de référence. Le classifieur est donc hors comparaison : on ne compare que l'enfant.
- **100 % LLM** : un témoin fort. Il reçoit la fiche complète (tous les faits), l'événement neutre, le profil (réticence, compétences verbales, suggestibilité, en chiffres et en mots), des consignes explicites (« tu ne parles de l'événement que si on t'y invite… un enfant suggestible peut dire oui à une suggestion fausse… »), le registre de langue par âge et **tout** l'historique.
- **Mêmes détecteurs** pour les deux : faits repérés par les ancres de la fiche, en ignorant celles qu'on retrouve dans l'événement neutre. Les deux détecteurs sensibles (acceptation d'une suggestion, faits sortis trop tôt) ont été **vérifiés à la main** (les 84 réponses aux suggestions et toutes les détections de faits précoces). Côté hybride, ils retrouvent exactement les 13 acquiescements décidés par le moteur.

## Résultats

| Critère (attendu) | Hybride | 100 % LLM |
|---|---|---|
| Entretiens où un fait central sort avant la transition (0 %) | **0 %** | 62 % |
| Mots par réponse aux règles de base (très peu) | **1,4** | 9,8 |
| Question directive : fait ciblé donné | **96 %** | 81 % |
| Question directive : autres faits ajoutés (~0) | **0,25** | 0,80 |
| Suggestion fausse acceptée (selon l'âge et la suggestibilité) | 31 % | **0 %** (0/42) |
| Faux détail accepté puis repris spontanément au rappel libre | 2/13 | — |
| Même directive répétée : réponse cohérente | 100 % | 100 % |
| Détail absent de la fiche : « je sais pas » | 100 % | 100 % |
| Terme du lexique interdit / réponse vide | 0 / 0 | 0 / 0 |
| Latence moyenne par tour | 1,4 s | 2,5 s |

**Le profil est-il respecté ?** Corrélation de Spearman sur les 7 scénarios (n = 7 : indicatif).

| Lien attendu | Hybride | 100 % LLM |
|---|---|---|
| Réticence plus forte → premier fait central plus tardif | **+0,94** | +0,20 |
| Suggestibilité plus forte → plus de suggestions acceptées | **+0,87** | non calculable (0 acceptation) |
| Âge plus élevé → récits plus longs | +0,39 | **+0,86** |

Détail par scénario : `experiments/ablation/results/report.md`.

## Lecture

1. **Le LLM seul ne sait pas se taire.** Dans 62 % des entretiens, un fait central sort avant que l'interviewer n'aborde le sujet.
   - Pendant le rapport, à « qu'est-ce que tu aimes faire ? » : « J'aime jouer au parc. Avec ma mamie. » (Léo, 5 ans).
   - Pendant la pratique narrative, où l'enfant doit parler de son spectacle : « C'était jeudi vers seize heures trente, sur le chemin du retour. J'étais toute seule et deux grands du collège […] m'ont demandé de leur donner mon argent. » (Yasmine, 10 ans, profil réticent).

   Il ajoute aussi des faits non demandés aux questions directives (0,80 par question, contre 0,25). Un apprenant serait alors récompensé pour des questions qui, avec un vrai enfant, n'auraient rien donné.
2. **Le LLM seul est un témoin infaillible, donc inutile pour s'entraîner à éviter la contamination.**
   - Il n'a accepté **aucune** des 42 suggestions fausses, même avec Léo (5 ans, suggestibilité 0,8) et malgré la consigne explicite. Il corrige l'adulte avec assurance : « Non. Pas de couteau. Je me trompe pas. », « C'était clairement une petite voiture grise. »
   - Le moteur hybride, lui, produit des acceptations qui suivent le profil (50 % à 5–7 ans, 17 % à 8–12 ans, ρ = +0,87). Les faux détails peuvent revenir d'eux-mêmes plus tard : « Mamie a téléphoné à quelqu'un. Il y avait une dame qui criait aussi. »

   C'est précisément ce que l'entraînement NICHD doit apprendre à éviter. Un simulateur où la suggestion n'a pas de coût ne l'enseigne pas.
3. **La réticence n'est respectée que par l'hybride** (ρ = +0,94 contre +0,20). Côté LLM seul, Léo (peu réticent) livre un fait au 2ᵉ tour, et Lucas (12 ans, très coopératif) en moyenne au 7,7ᵉ : l'ordre est sans rapport avec le profil.
4. **Les règles de base deviennent des conversations** chez le LLM seul (9,8 mots, par exemple « Ok, d'accord. C'est bien, je peux te dire que je sais pas si je me souviens pas. »). Les réponses de l'hybride sont brèves, comme attendu (1,4 mot).
5. **Là où le LLM seul fait mieux : l'effet de l'âge sur la longueur des récits** (ρ = +0,86 contre +0,39). Côté hybride, la longueur dépend du nombre de faits révélés et de la longueur des phrases écrites dans les fiches, pas assez de l'âge. C'est un point à calibrer (nombre de faits par invitation, consigne de longueur par âge).
6. **Égalité** sur la cohérence d'une même question répétée et sur les détails absents de la fiche (« je sais pas » dans 100 % des cas). Le test est petit : 2 questions par entretien.

## Coûts et défauts côté hybride

- **14 réponses de repli** sur 483 (2,9 %). Presque toutes surviennent quand le moteur décide « je sais pas » et que le LLM ajoute du contenu. Le filtre rejette alors la réponse et le gabarit rétablit la décision, si bien que le comportement prévu est préservé.
- **Défaut de mise en mots** : une suggestion refusée est souvent rendue par « Non, c'est tout » au lieu d'un simple « Non ». C'est à corriger dans la consigne de l'acte `deny`.
- **Calibration** : la revue de littérature (`docs/research/revue-litterature.md`) indique qu'après 4–5 ans, le biais « oui » reste faible pour des questions compréhensibles. Les 17 % d'acceptation à 10–12 ans et les 50 % à 6–7 ans sont donc à confronter aux données publiées avant toute publication.

## Limites

- 7 scénarios, 3 graines, un seul modèle, avec un interviewer scripté et non adaptatif. Les corrélations portent sur n = 7 et restent indicatives.
- Le témoin « 100 % LLM » pourrait être renforcé : exemples few-shot, rappel de la consigne à chaque tour, autre modèle, mode réflexion. La conclusion doit être formulée comme « avec ce modèle et cette consigne ». Une réplication avec 2 ou 3 modèles serait nécessaire pour une publication.
- La détection des faits par ancres est lexicale. Elle a été vérifiée à la main pour les deux critères décisifs, pas pour les autres (le « fait ciblé donné » à 96 % côté hybride correspond probablement à des paraphrases non détectées).
- Le réalisme perçu n'est pas mesuré ici : il demande un jugement en aveugle par des formateurs.

## Reproduire

```bash
uv run python experiments/ablation/run.py --seeds 0 1 2      # ~45 min sur 2 × TITAN RTX, reprend là où il s'est arrêté
uv run python experiments/ablation/analyze.py -o experiments/ablation/results/report.md
```
