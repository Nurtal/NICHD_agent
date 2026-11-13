# Évaluations du classifieur

Jeu de test : `src/nichd_sim/skill/testset.jsonl` (104 énoncés sur les scénarios s01–s03, dont 12 ambigus), disjoint des exemples few-shot. Modèle `qwen3.8:latest` (27B, Q4_K_M) sur 2 × TITAN RTX.

| Skill | Réflexion | κ (type) | Type | Cible | Indice de phase | Latence médiane / max | Rapport |
|---|---|---|---|---|---|---|---|
| 0.1.0 | off | 0,956 | 96,2 % | 83,3 % | 96,2 % | 2,6 s / 8,0 s | [lien](classifier_skill-0.1.0_qwen3.8.md) |
| 0.2.0 | off | 0,956 | 96,2 % | 90,7 % | 96,2 % | 3,6 s / 10,4 s | [lien](classifier_skill-0.2.0_qwen3.8.md) |
| 0.2.0 | low | 0,945 | 95,2 % | 88,9 % | 98,1 % | 8,4 s / 48,6 s | [lien](classifier_skill-0.2.0_qwen3.8_think-low.md) |
| **0.2.0** | **medium** | **0,978** | **98,1 %** | 90,7 % | 96,2 % | 13,1 s / 60,9 s | [lien](classifier_skill-0.2.0_qwen3.8_think-medium.md) |

**Réglage par défaut : skill 0.2.0, réflexion `medium`** — le plus précis mesuré (100 % sur les énoncés non ambigus). La priorité actuelle est de vérifier que l'approche fonctionne ; la latence (13 s médiane par classification, jusqu'à ~1 min) sera optimisée plus tard (`--classifier-think off` pour une démonstration fluide).

Prudence : sur 104 énoncés, les écarts entre réglages portent sur 2 à 3 énoncés ; une mesure sur un jeu plus large (scénarios s04–s07) affinerait la comparaison.
