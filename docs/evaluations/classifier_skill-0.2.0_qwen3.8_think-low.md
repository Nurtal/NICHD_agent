# Évaluation du classifieur NICHD

- Modèle : `qwen3.8:latest (réflexion : low)` — skill v0.2.0 — 104 énoncés du jeu de test
- **Kappa de Cohen (type)** : **0.945** (objectif v1 ≥ 0.7 : atteint)
- Exactitude du type : 95.2% (non ambigus : 98.9%, ambigus : 66.7%)
- Exactitude de la cible : 88.9%
- Exactitude de l'indice de phase : 98.1%
- Latence : médiane 8.39 s, max 48.61 s

## Confusions de type (attendu → prédit)

- invitation → suggestive : 2
- other → support : 1
- invitation → support : 1
- invitation → compound : 1

## Erreurs

| id | énoncé | attendu | prédit |
|---|---|---|---|
| ts012 | Ta mamie m'a dit que tu as vu quelque chose au parc. Raconte-moi. *(ambigu)* | invitation / None | suggestive / b_parc |
| ts030 | Quand le monsieur au blouson rouge a cassé les lunettes, tu étais où ? | suggestive / d_lunettes | suggestive / d_banc |
| ts032 | Il est parti où et ta mamie a fait quoi ? | compound / a_part | compound / out_of_scenario |
| ts034 | Tu aimes les glaces au chocolat ? *(ambigu)* | other / None | support / None |
| ts039 | Qu'est-ce que tu aimes faire à l'école ? | invitation / None | support / None |
| ts047 | Je vois que tu as une marque sur le bras. Dis-moi tout sur cette marque. *(ambigu)* | invitation / None | suggestive / a_bleu |
| ts048 | Est-ce que quelqu'un t'a fait mal ? | option_posing / d_tape | option_posing / out_of_scenario |
| ts054 | Il t'a attrapé quel bras ? | directive / d_bras | directive / out_of_scenario |
| ts079 | Je crois que tu as vu quelque chose mardi. Dis-moi tout. *(ambigu)* | invitation / None | compound / b_mardi |
| ts088 | C'était un portefeuille noir, hein ? *(ambigu)* | suggestive / d_vol | suggestive / out_of_scenario |
| ts092 | Où était ton frère pendant ce temps ? | directive / b_yanis | directive / out_of_scenario |
