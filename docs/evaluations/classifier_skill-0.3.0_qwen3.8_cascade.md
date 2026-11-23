# Évaluation du classifieur NICHD

- Modèle : `qwen3.8:latest (réflexion : cascade)` — skill v0.3.0 — 133 énoncés du jeu de test
- **Kappa de Cohen (type)** : **0.948** (objectif v1 ≥ 0.7 : atteint)
- Exactitude du type : 95.5% (non ambigus : 97.5%, ambigus : 80.0%)
- Exactitude de la cible : 83.3%
- Exactitude de l'indice de phase : 97.0%
- Latence : médiane 4.99 s, max 66.25 s

## Champs du skill 0.3.0

| Champ | Exactitude | Rappel (valeurs renseignées) | n |
|---|---|---|---|
| `segment` | 100.0% | 100.0% | 6 |
| `knowledge_question` | 98.5% | 100.0% | 6 |
| `ground_rule_kind` | 100.0% | 100.0% | 13 |
| `practice_kind` | 97.0% | 100.0% | 11 |
| `causal` | 100.0% | 100.0% | 8 |

## Confusions de type (attendu → prédit)

- invitation → cued_invitation : 2
- option_posing → directive : 2
- other → support : 1
- invitation → support : 1

## Erreurs

| id | énoncé | attendu | prédit |
|---|---|---|---|
| ts021 | Comment il l'a poussé ? | directive / d_pousse | directive / out_of_scenario |
| ts023 | Qu'est-ce qu'ils criaient ? | directive / d_crient | directive / out_of_scenario |
| ts030 | Quand le monsieur au blouson rouge a cassé les lunettes, tu étais où ? | suggestive / d_lunettes | suggestive / b_parc |
| ts032 | Il est parti où et ta mamie a fait quoi ? | compound / a_part | compound / out_of_scenario |
| ts034 | Tu aimes les glaces au chocolat ? *(ambigu)* | other / None | support / None |
| ts039 | Qu'est-ce que tu aimes faire à l'école ? | invitation / None | support / None |
| ts047 | Je vois que tu as une marque sur le bras. Dis-moi tout sur cette marque. *(ambigu)* | invitation / None | cued_invitation / a_bleu |
| ts048 | Est-ce que quelqu'un t'a fait mal ? | option_posing / d_tape | option_posing / d_bras |
| ts054 | Il t'a attrapé quel bras ? | directive / d_bras | directive / out_of_scenario |
| ts088 | C'était un portefeuille noir, hein ? *(ambigu)* | suggestive / d_vol | suggestive / out_of_scenario |
| ts092 | Où était ton frère pendant ce temps ? | directive / b_yanis | directive / out_of_scenario |
| ts106 | Et ce qui s'est passé avant que ça commence, raconte-moi. | invitation / None | cued_invitation / d_pousse |
| ts108 | Tu as parlé de la dame. Raconte-moi tout ce qui s'est passé après qu'elle a pris le portefeuille. *(ambigu)* | cued_invitation / d_dame | cued_invitation / d_vol |
| ts115 | Est-ce que tu te rappelles de quelle couleur était son manteau ? | option_posing / d_dame | directive / d_dame |
| ts117 | Est-ce que tu peux me dire où tu étais ? *(ambigu)* | option_posing / b_cuisine | directive / b_cuisine |
| ts122 | Pourquoi tu n'as rien dit à ta maman ? | directive / out_of_scenario | directive / a_secret |
| ts123 | Comment ça se fait que la boulangère n'a rien vu ? | directive / out_of_scenario | directive / d_boulangere |
