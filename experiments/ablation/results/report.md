# Ablation v2 : enfant hybride vs enfant 100 % LLM, plusieurs modèles locaux

Modèles (Ollama, locaux) : `qwen3.8:latest`, `gemma4:latest`, `mistral:latest`, `phi4:latest`. Température 0,7, réflexion désactivée. Entretiens par condition : Hybride 84, 100 % LLM 84, 100 % LLM renforcé 84 (7 scénarios × 3 graines × modèles), 23 tours scriptés identiques. Mêmes détecteurs pour toutes les conditions.

## Synthèse (moyenne sur les modèles, [min – max])

| Critère (attendu) | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Entretiens où un fait central sort avant la transition (0 %) | 0 % [0 % – 0 %] | 68 % [24 % – 100 %] | 55 % [10 % – 95 %] |
| Mots par réponse aux règles de base (très peu) | 2.8 [1.3 – 4.4] | 11.8 [9.7 – 14.3] | 8.6 [3.8 – 15.0] |
| Directive : fait ciblé donné | 96 % [96 % – 96 %] | 86 % [81 % – 92 %] | 82 % [77 % – 86 %] |
| Directive : faits nouveaux ajoutés en plus du fait ciblé (~0) | 0.04 [0.04 – 0.04] | 0.13 [0.02 – 0.29] | 0.14 [0.06 – 0.23] |
| Hors scénario : « je sais pas » | 84 % [60 % – 98 %] | 83 % [67 % – 100 %] | 74 % [45 % – 100 %] |
| Suggestion fausse acceptée | 16 % [14 % – 17 %] | 3 % [0 % – 7 %] | 22 % [10 % – 43 %] |
| Écart moyen au taux d'acceptation visé par profil (0) | 7 % [7 % – 8 %] | 13 % [11 % – 14 %] | 17 % [9 % – 32 %] |
| ρ réticence → dévoilement tardif (> 0) | +0.94 [+0.94 – +0.94] | +0.00 [-0.18 – +0.20] | +0.18 [-0.10 – +0.77] |
| ρ suggestibilité → acceptations (> 0) | +0.92 [+0.81 – +0.95] | +0.20 [+0.00 – +0.41] | +0.87 [+0.80 – +0.97] |
| ρ âge → mots par récit (> 0) | +0.77 [+0.68 – +0.89] | +0.78 [+0.68 – +0.89] | +0.60 [+0.04 – +0.93] |
| ρ âge → faits par récit (> 0) | +0.86 [+0.81 – +0.93] | +0.69 [+0.40 – +0.93] | +0.70 [+0.64 – +0.79] |
| Réponses hors rôle par entretien (0) | 0.02 [0.00 – 0.10] | 0.00 [0.00 – 0.00] | 0.55 [0.00 – 2.19] |
| Latence moyenne par tour | 0.9 s [0.4 s – 1.4 s] | 1.9 s [0.4 s – 5.1 s] | 1.3 s [0.3 s – 2.5 s] |

Taux d'acceptation visé par profil (moteur v2, après deux règles de base) : s01 32 %, s02 12 %, s03 5 %, s04 26 %, s05 14 %, s06 5 %, s07 5 %.

## Par modèle

| Modèle | Condition | Fait central précoce | Faits nouveaux ajoutés / directive | Suggestions acceptées | Écart au visé | ρ réticence | ρ suggestibilité | ρ âge | Replis | Faux détail repris |
|---|---|---|---|---|---|---|---|---|---|---|
| `qwen3.8:latest` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.68 | 16 | 2/7 |
| `qwen3.8:latest` | 100 % LLM | 62 % | 0.10 | 0 % | 14 % | +0.20 | +nan | +0.86 | — | 0/0 |
| `qwen3.8:latest` | 100 % LLM renforcé | 29 % | 0.18 | 12 % | 9 % | +0.77 | +0.80 | +0.89 | — | 0/5 |
| `gemma4:latest` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.68 | 10 | 3/7 |
| `gemma4:latest` | 100 % LLM | 24 % | 0.29 | 5 % | 11 % | +0.11 | +0.41 | +0.89 | — | 0/2 |
| `gemma4:latest` | 100 % LLM renforcé | 10 % | 0.23 | 43 % | 32 % | +0.10 | +0.97 | +0.93 | — | 0/18 |
| `mistral:latest` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.89 | 58 | 3/7 |
| `mistral:latest` | 100 % LLM | 100 % | 0.13 | 7 % | 11 % | -0.18 | +0.00 | +0.68 | — | 1/3 |
| `mistral:latest` | 100 % LLM renforcé | 95 % | 0.08 | 24 % | 17 % | -0.10 | +0.91 | +0.54 | — | 0/10 |
| `phi4:latest` | Hybride | 0 % | 0.04 | 14 % | 8 % | +0.94 | +0.81 | +0.82 | 55 | 3/6 |
| `phi4:latest` | 100 % LLM | 86 % | 0.02 | 0 % | 14 % | -0.11 | +nan | +0.68 | — | 0/0 |
| `phi4:latest` | 100 % LLM renforcé | 86 % | 0.06 | 10 % | 10 % | -0.04 | +0.80 | +0.04 | — | 1/4 |

ρ : corrélation de Spearman sur les 7 scénarios (n = 7, indicatif) ; « nan » quand une condition ne varie pas (par exemple aucune suggestion acceptée).

## Par scénario (moyenne sur les modèles)

| Scénario | Âge | Réticence | Suggestibilité | Visé | Acceptées Hybride | 1er fait Hybride | Acceptées 100 % LLM | 1er fait 100 % LLM | Acceptées 100 % LLM renforcé | 1er fait 100 % LLM renforcé |
|---|---|---|---|---|---|---|---|---|---|---|
| s01_bagarre_parc | 5 | 0.2 | 0.8 | 32 % | 50 % | 8.0 | 0 % | 1.8 | 71 % | 4.7 |
| s02_violences_maison | 8 | 0.65 | 0.4 | 12 % | 17 % | 11.0 | 0 % | 6.4 | 4 % | 7.5 |
| s03_vol_boulangerie | 11 | 0.1 | 0.2 | 5 % | 0 % | 8.0 | 0 % | 6.9 | 0 % | 7.1 |
| s04_violences_conjugales | 6 | 0.55 | 0.6 | 26 % | 33 % | 11.0 | 12 % | 6.9 | 54 % | 7.4 |
| s05_negligence | 7 | 0.4 | 0.5 | 14 % | 12 % | 9.0 | 4 % | 4.1 | 21 % | 7.2 |
| s06_racket | 10 | 0.45 | 0.25 | 5 % | 0 % | 9.0 | 0 % | 8.0 | 4 % | 7.9 |
| s07_delit_fuite | 12 | 0.05 | 0.15 | 5 % | 0 % | 8.0 | 4 % | 7.3 | 0 % | 7.8 |
