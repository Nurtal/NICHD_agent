# Évaluation du classifieur NICHD

- Modèle : `qwen3.8:latest` — skill v0.1.0 — 104 énoncés du jeu de test
- **Kappa de Cohen (type)** : **0.956** (objectif v1 ≥ 0.7 : atteint)
- Exactitude du type : 96.2% (non ambigus : 98.9%, ambigus : 75.0%)
- Exactitude de la cible : 83.3%
- Exactitude de l'indice de phase : 96.2%
- Latence : médiane 2.62 s, max 8.00 s

## Confusions de type (attendu → prédit)

- other → support : 1
- invitation → support : 1
- invitation → cued_invitation : 1
- option_posing → suggestive : 1

## Erreurs

| id | énoncé | attendu | prédit |
|---|---|---|---|
| ts013 | Est-ce que quelqu'un s'est battu au parc ? | option_posing / d_pousse | option_posing / b_parc |
| ts024 | Il était habillé comment, le voisin ? | directive / out_of_scenario | directive / d_messieurs |
| ts025 | Le monsieur au blouson rouge, il était grand ou petit ? | option_posing / out_of_scenario | option_posing / d_messieurs |
| ts032 | Il est parti où et ta mamie a fait quoi ? | compound / a_part | compound / a_telephone |
| ts034 | Tu aimes les glaces au chocolat ? *(ambigu)* | other / None | support / None |
| ts039 | Qu'est-ce que tu aimes faire à l'école ? | invitation / None | support / None |
| ts047 | Je vois que tu as une marque sur le bras. Dis-moi tout sur cette marque. *(ambigu)* | invitation / None | cued_invitation / a_bleu |
| ts048 | Est-ce que quelqu'un t'a fait mal ? | option_posing / d_tape | option_posing / out_of_scenario |
| ts056 | Il t'a tapée avec une ceinture ? *(ambigu)* | option_posing / d_tape | suggestive / d_tape |
| ts085 | Elle avait quel âge ? | directive / out_of_scenario | directive / d_dame |
| ts086 | Elle avait les cheveux blonds ou bruns ? | option_posing / out_of_scenario | option_posing / d_dame |
| ts087 | Elle a mis le portefeuille où ? | directive / d_sac | directive / d_poche |
| ts096 | Tu étais où exactement et tu as vu son visage ? | compound / out_of_scenario | compound / b_boulangerie |
