# Ablation v2 : enfant hybride vs enfant 100 % LLM, plusieurs modèles locaux

Modèles (Ollama, locaux) : `qwen3.8:latest`, `gemma4:31b`, `gemma4:latest`, `gpt-oss:20b`, `mistral-small3.2:24b`, `mistral:latest`, `olmo-3.1:32b-instruct`, `phi4:latest`. Température 0,7, réflexion désactivée. Entretiens par condition : Hybride 168, 100 % LLM 168, 100 % LLM renforcé 168 (7 scénarios × 3 graines × modèles), 23 tours scriptés identiques. Mêmes détecteurs pour toutes les conditions.

## Synthèse (moyenne sur les modèles, [min – max])

| Critère (attendu) | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Entretiens où un fait central sort avant la transition (0 %) | 0 % [0 % – 0 %] | 55 % [10 % – 100 %] | 46 % [10 % – 95 %] |
| Mots par réponse aux règles de base (très peu) | 2.3 [1.0 – 4.4] | 8.6 [4.0 – 14.3] | 6.1 [2.4 – 15.0] |
| Directive : fait ciblé donné | 96 % [96 % – 96 %] | 81 % [71 % – 92 %] | 78 % [67 % – 86 %] |
| Directive : faits nouveaux ajoutés en plus du fait ciblé (~0) | 0.04 [0.04 – 0.04] | 0.14 [0.02 – 0.29] | 0.14 [0.06 – 0.23] |
| Hors scénario : « je sais pas » | 89 % [60 % – 100 %] | 87 % [67 % – 100 %] | 80 % [45 % – 100 %] |
| Suggestion fausse acceptée | 16 % [14 % – 17 %] | 9 % [0 % – 31 %] | 19 % [0 % – 43 %] |
| Écart moyen au taux d'acceptation visé par profil (0) | 7 % [7 % – 8 %] | 16 % [11 % – 25 %] | 17 % [9 % – 32 %] |
| ρ réticence → dévoilement tardif (> 0) | +0.94 [+0.94 – +0.94] | +0.19 [-0.18 – +0.88] | +0.33 [-0.10 – +0.77] |
| ρ suggestibilité → acceptations (> 0) | +0.94 [+0.81 – +0.95] | +0.56 [+0.00 – +0.91] | +0.85 [+0.80 – +0.97] |
| ρ âge → mots par récit (> 0) | +0.72 [+0.61 – +0.89] | +0.77 [+0.54 – +0.93] | +0.69 [+0.04 – +0.93] |
| ρ âge → faits par récit (> 0) | +0.82 [+0.59 – +0.93] | +0.65 [+0.40 – +0.93] | +0.71 [+0.57 – +0.93] |
| Réponses hors rôle par entretien (0) | 0.01 [0.00 – 0.10] | 0.58 [0.00 – 4.24] | 0.67 [0.00 – 2.43] |
| Latence moyenne par tour | 1.2 s [0.4 s – 2.2 s] | 2.0 s [0.4 s – 5.1 s] | 1.6 s [0.3 s – 3.7 s] |

Taux d'acceptation visé par profil (moteur v2, après deux règles de base) : s01 32 %, s02 12 %, s03 5 %, s04 26 %, s05 14 %, s06 5 %, s07 5 %.

## Par modèle

| Modèle | Condition | Fait central précoce | Faits nouveaux ajoutés / directive | Suggestions acceptées | Écart au visé | ρ réticence | ρ suggestibilité | ρ âge | Replis | Faux détail repris |
|---|---|---|---|---|---|---|---|---|---|---|
| `qwen3.8:latest` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.68 | 16 | 2/7 |
| `qwen3.8:latest` | 100 % LLM | 62 % | 0.10 | 0 % | 14 % | +0.20 | +nan | +0.86 | — | 0/0 |
| `qwen3.8:latest` | 100 % LLM renforcé | 29 % | 0.18 | 12 % | 9 % | +0.77 | +0.80 | +0.89 | — | 0/5 |
| `gemma4:31b` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.61 | 7 | 2/7 |
| `gemma4:31b` | 100 % LLM | 10 % | 0.15 | 31 % | 25 % | +0.88 | +0.91 | +0.93 | — | 2/13 |
| `gemma4:31b` | 100 % LLM renforcé | 19 % | 0.12 | 19 % | 17 % | +0.20 | +0.80 | +0.86 | — | 8/8 |
| `gemma4:latest` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.68 | 10 | 3/7 |
| `gemma4:latest` | 100 % LLM | 24 % | 0.29 | 5 % | 11 % | +0.11 | +0.41 | +0.89 | — | 0/2 |
| `gemma4:latest` | 100 % LLM renforcé | 10 % | 0.23 | 43 % | 32 % | +0.10 | +0.97 | +0.93 | — | 0/18 |
| `gpt-oss:20b` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.68 | 3 | 2/7 |
| `gpt-oss:20b` | 100 % LLM | 52 % | 0.08 | 29 % | 22 % | -0.04 | +0.91 | +0.75 | — | 0/12 |
| `gpt-oss:20b` | 100 % LLM renforcé | 62 % | 0.06 | 29 % | 22 % | +0.61 | +0.90 | +0.93 | — | 0/12 |
| `mistral-small3.2:24b` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.75 | 23 | 2/7 |
| `mistral-small3.2:24b` | 100 % LLM | 33 % | 0.26 | 0 % | 14 % | +0.64 | +nan | +0.86 | — | 0/0 |
| `mistral-small3.2:24b` | 100 % LLM renforcé | 14 % | 0.21 | 19 % | 17 % | +0.68 | +0.80 | +0.50 | — | 3/8 |
| `mistral:latest` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.89 | 58 | 3/7 |
| `mistral:latest` | 100 % LLM | 100 % | 0.13 | 7 % | 11 % | -0.18 | +0.00 | +0.68 | — | 1/3 |
| `mistral:latest` | 100 % LLM renforcé | 95 % | 0.08 | 24 % | 17 % | -0.10 | +0.91 | +0.54 | — | 0/10 |
| `olmo-3.1:32b-instruct` | Hybride | 0 % | 0.04 | 17 % | 7 % | +0.94 | +0.95 | +0.64 | 17 | 3/7 |
| `olmo-3.1:32b-instruct` | 100 % LLM | 71 % | 0.12 | 0 % | 14 % | +0.00 | +nan | +0.54 | — | 0/0 |
| `olmo-3.1:32b-instruct` | 100 % LLM renforcé | 52 % | 0.18 | 0 % | 14 % | +0.41 | +nan | +0.86 | — | 0/0 |
| `phi4:latest` | Hybride | 0 % | 0.04 | 14 % | 8 % | +0.94 | +0.81 | +0.82 | 55 | 3/6 |
| `phi4:latest` | 100 % LLM | 86 % | 0.02 | 0 % | 14 % | -0.11 | +nan | +0.68 | — | 0/0 |
| `phi4:latest` | 100 % LLM renforcé | 86 % | 0.06 | 10 % | 10 % | -0.04 | +0.80 | +0.04 | — | 1/4 |

ρ : corrélation de Spearman sur les 7 scénarios (n = 7, indicatif) ; « nan » quand une condition ne varie pas (par exemple aucune suggestion acceptée).

## Par scénario (moyenne sur les modèles)

| Scénario | Âge | Réticence | Suggestibilité | Visé | Acceptées Hybride | 1er fait Hybride | Acceptées 100 % LLM | 1er fait 100 % LLM | Acceptées 100 % LLM renforcé | 1er fait 100 % LLM renforcé |
|---|---|---|---|---|---|---|---|---|---|---|
| s01_bagarre_parc | 5 | 0.2 | 0.8 | 32 % | 50 % | 8.0 | 25 % | 3.0 | 67 % | 6.0 |
| s02_violences_maison | 8 | 0.65 | 0.4 | 12 % | 17 % | 11.0 | 0 % | 7.1 | 2 % | 7.9 |
| s03_vol_boulangerie | 11 | 0.1 | 0.2 | 5 % | 0 % | 8.0 | 0 % | 7.2 | 0 % | 7.0 |
| s04_violences_conjugales | 6 | 0.55 | 0.6 | 26 % | 33 % | 11.0 | 25 % | 7.9 | 50 % | 8.0 |
| s05_negligence | 7 | 0.4 | 0.5 | 14 % | 15 % | 9.0 | 10 % | 5.2 | 15 % | 7.1 |
| s06_racket | 10 | 0.45 | 0.25 | 5 % | 0 % | 9.0 | 0 % | 8.2 | 2 % | 9.0 |
| s07_delit_fuite | 12 | 0.05 | 0.15 | 5 % | 0 % | 8.0 | 2 % | 7.2 | 0 % | 7.4 |
