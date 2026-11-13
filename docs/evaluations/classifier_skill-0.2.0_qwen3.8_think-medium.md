# Évaluation du classifieur NICHD

- Modèle : `qwen3.8:latest (réflexion : medium)` — skill v0.2.0 — 104 énoncés du jeu de test
- **Kappa de Cohen (type)** : **0.978** (objectif v1 ≥ 0.7 : atteint)
- Exactitude du type : 98.1% (non ambigus : 100.0%, ambigus : 83.3%)
- Exactitude de la cible : 90.7%
- Exactitude de l'indice de phase : 96.2%
- Latence : médiane 13.10 s, max 60.92 s

## Confusions de type (attendu → prédit)

- other → support : 1
- invitation → suggestive : 1

## Erreurs

| id | énoncé | attendu | prédit |
|---|---|---|---|
| ts032 | Il est parti où et ta mamie a fait quoi ? | compound / a_part | compound / out_of_scenario |
| ts034 | Tu aimes les glaces au chocolat ? *(ambigu)* | other / None | support / None |
| ts047 | Je vois que tu as une marque sur le bras. Dis-moi tout sur cette marque. *(ambigu)* | invitation / None | suggestive / a_bleu |
| ts048 | Est-ce que quelqu'un t'a fait mal ? | option_posing / d_tape | option_posing / d_bras |
| ts054 | Il t'a attrapé quel bras ? | directive / d_bras | directive / out_of_scenario |
| ts088 | C'était un portefeuille noir, hein ? *(ambigu)* | suggestive / d_vol | suggestive / out_of_scenario |
| ts092 | Où était ton frère pendant ce temps ? | directive / b_yanis | directive / b_boulangerie |
