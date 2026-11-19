# Évaluation du classifieur NICHD

- Modèle : `qwen3.8:latest (réflexion : medium)` — skill v0.3.0 — 133 énoncés du jeu de test
- **Kappa de Cohen (type)** : **0.948** (objectif v1 ≥ 0.7 : atteint)
- Exactitude du type : 95.5% (non ambigus : 96.6%, ambigus : 86.7%)
- Exactitude de la cible : 86.4%
- Exactitude de l'indice de phase : 95.5%
- Latence : médiane 13.62 s, max 72.17 s

## Champs du skill 0.3.0

| Champ | Exactitude | Rappel (valeurs renseignées) | n |
|---|---|---|---|
| `segment` | 100.0% | 100.0% | 6 |
| `knowledge_question` | 100.0% | 100.0% | 6 |
| `ground_rule_kind` | 100.0% | 100.0% | 13 |
| `practice_kind` | 97.7% | 90.9% | 11 |
| `causal` | 99.2% | 87.5% | 8 |

## Confusions de type (attendu → prédit)

- option_posing → directive : 3
- other → support : 1
- invitation → suggestive : 1
- invitation → cued_invitation : 1

## Erreurs

| id | énoncé | attendu | prédit |
|---|---|---|---|
| ts023 | Qu'est-ce qu'ils criaient ? | directive / d_crient | directive / out_of_scenario |
| ts032 | Il est parti où et ta mamie a fait quoi ? | compound / a_part | compound / out_of_scenario |
| ts034 | Tu aimes les glaces au chocolat ? *(ambigu)* | other / None | support / None |
| ts047 | Je vois que tu as une marque sur le bras. Dis-moi tout sur cette marque. *(ambigu)* | invitation / None | suggestive / a_bleu |
| ts048 | Est-ce que quelqu'un t'a fait mal ? | option_posing / d_tape | option_posing / out_of_scenario |
| ts054 | Il t'a attrapé quel bras ? | directive / d_bras | directive / out_of_scenario |
| ts088 | C'était un portefeuille noir, hein ? *(ambigu)* | suggestive / d_vol | suggestive / out_of_scenario |
| ts092 | Où était ton frère pendant ce temps ? | directive / b_yanis | directive / b_boulangerie |
| ts106 | Et ce qui s'est passé avant que ça commence, raconte-moi. | invitation / None | cued_invitation / d_pousse |
| ts108 | Tu as parlé de la dame. Raconte-moi tout ce qui s'est passé après qu'elle a pris le portefeuille. *(ambigu)* | cued_invitation / d_dame | cued_invitation / d_vol |
| ts114 | Tu sais comment il s'appelle, le monsieur au blouson rouge ? | option_posing / out_of_scenario | directive / out_of_scenario |
| ts115 | Est-ce que tu te rappelles de quelle couleur était son manteau ? | option_posing / d_dame | directive / d_dame |
| ts118 | Tu sais qui a appelé la police ? | option_posing / a_police | directive / a_police |
| ts122 | Pourquoi tu n'as rien dit à ta maman ? | directive / out_of_scenario | directive / a_secret |
| ts123 | Comment ça se fait que la boulangère n'a rien vu ? | directive / out_of_scenario | directive / d_boulangere |
