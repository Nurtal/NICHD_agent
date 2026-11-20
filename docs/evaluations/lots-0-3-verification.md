# Vérification des lots 0 à 3 avec les modèles locaux

Points 3 et 4 de la vérification commune du [plan d'adaptations](../plans/adaptations-litterature.md), après les lots 0
à 3 (2026-11-20).

## Ablation : enfant hybride contre LLM seul

`experiments/ablation/run.py --models gemma4:31b --seeds 0 1 --conditions hybrid`. Les entretiens « LLM seul »
reprennent ceux de l'ablation v3 (mêmes scripts, mêmes graines), car ils ne dépendent pas du moteur. Rapport :
[results/v4-lots/report.md](../../experiments/ablation/results/v4-lots/report.md).

| Critère | Hybride v3 | Hybride v4 (lots 0–3) | LLM seul |
|---|---|---|---|
| Fait central dit avant la transition | 0 % | **0 %** | 7 % |
| Faits nouveaux ajoutés à une directive | 0.04 | 0.04 | 0.14 |
| Suggestion fausse acceptée | 17 % | 7 % | 32 % |
| Réponses hors rôle par entretien | 0 | 0 | 4.2 |

La baisse de l'acceptation (17 → 7 %) tient surtout au petit échantillon (2 suggestions × 7 scénarios × 2 graines).
Le moteur seul (classifieur manuel, 400 graines, mêmes scripts) ne baisse que de 0 à 3 points, et les taux visés par
profil restent tenus :

| Scénario | Avant les lots | Après |
|---|---|---|
| s01 | 32 % | 30 % |
| s02 | 12 % | 11 % |
| s03 | 4 % | 4 % |
| s04 | 27 % | 24 % |
| s05 | 14 % | 12 % |
| s06 | 4 % | 4 % |
| s07 | 4 % | 4 % |

## Entretiens réels

Classifieur `qwen3.8` (réflexion « medium ») et réalisateur `gemma4:31b`. Les deux passes ont été jouées l'une après
l'autre pour ne charger qu'un seul gros modèle à la fois sur les GPU partagés
(`experiments/ablation/two_pass_live.py`) :
1. classification, avec le réalisateur gabarit ;
2. réalisation, à partir des classifications enregistrées.

Les décisions sont identiques dans les deux passes. Transcriptions :
[s01, Léo](entretiens-lots/s01-leo.md) et [s08, Emma](entretiens-lots/s08-emma.md).

**Relu à la main.** Aucun repli, et aucun fait hors liste.
- « Raconte-moi la fin » donne bien la fin (segment `after`), alors que les démos donnaient le début.
- « Tu te souviens comment il s'appelait ? » est reconnu comme question de connaissance. Le tirage n'a pas donné un
  « oui » seul : l'enfant répond comme à une directive.
- La promesse est reconnue (`ground_rule_kind = promise`) et la dissimulation passe de 0,56 à 0,41. Emma nomme ensuite
  Karim, mais garde la version de l'escalier et nie le secret. Elle livre « Karim a crié » au dernier récit.
- « Est-ce que quelqu'un t'a fait mal ? » est classé hors scénario, donc répondu « Ben non ». C'est l'erreur connue
  ts048 du classifieur.

**Pas couvert par ces deux entretiens.**
- La fuite (A9) : Emma a dit la vérité sur Karim, il n'y avait donc pas de mensonge à contredire. Elle est couverte par
  les tests et le rapport de fidélité.
- Les deux questions sur les chaussures n'ont pas été comptées comme une répétition. Une question hors scénario est
  identifiée par sa formulation, et l'ajout de « le garçon » la change. Le compteur de répétitions ne reconnaît donc
  qu'une reprise mot pour mot de ces questions.
