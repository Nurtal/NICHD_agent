# Évaluation du classifieur NICHD

- Modèle : `qwen3.8:latest` — skill v0.2.0 — 104 énoncés du jeu de test
- **Kappa de Cohen (type)** : **0.956** (objectif v1 ≥ 0.7 : atteint)
- Exactitude du type : 96.2% (non ambigus : 98.9%, ambigus : 75.0%)
- Exactitude de la cible : 90.7%
- Exactitude de l'indice de phase : 96.2%
- Latence : médiane 3.55 s, max 10.35 s

## Confusions de type (attendu → prédit)

- other → support : 1
- invitation → support : 1
- invitation → cued_invitation : 1
- option_posing → suggestive : 1

## Erreurs

| id | énoncé | attendu | prédit |
|---|---|---|---|
| ts025 | Le monsieur au blouson rouge, il était grand ou petit ? | option_posing / out_of_scenario | option_posing / d_messieurs |
| ts032 | Il est parti où et ta mamie a fait quoi ? | compound / a_part | compound / a_telephone |
| ts034 | Tu aimes les glaces au chocolat ? *(ambigu)* | other / None | support / None |
| ts039 | Qu'est-ce que tu aimes faire à l'école ? | invitation / None | support / None |
| ts047 | Je vois que tu as une marque sur le bras. Dis-moi tout sur cette marque. *(ambigu)* | invitation / None | cued_invitation / a_bleu |
| ts048 | Est-ce que quelqu'un t'a fait mal ? | option_posing / d_tape | option_posing / out_of_scenario |
| ts056 | Il t'a tapée avec une ceinture ? *(ambigu)* | option_posing / d_tape | suggestive / d_tape |
| ts087 | Elle a mis le portefeuille où ? | directive / d_sac | directive / d_poche |
| ts092 | Où était ton frère pendant ce temps ? | directive / b_yanis | directive / out_of_scenario |
