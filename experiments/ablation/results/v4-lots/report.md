# Ablation v2 : enfant hybride vs enfant 100 % LLM, plusieurs modèles locaux

Modèles (Ollama, locaux) : `gemma4:31b`. Température 0,7, réflexion désactivée. Entretiens par condition : Hybride 14, 100 % LLM 14, 100 % LLM renforcé 14 (7 scénarios × 3 graines × modèles), 23 tours scriptés identiques. Mêmes détecteurs pour toutes les conditions.

## Synthèse (moyenne sur les modèles, [min – max])

| Critère (attendu) | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Entretiens où un fait central sort avant la transition (0 %) | 0 % [0 % – 0 %] | 7 % [7 % – 7 %] | 29 % [29 % – 29 %] |
| Mots par réponse aux règles de base (très peu) | 1.0 [1.0 – 1.0] | 5.5 [5.5 – 5.5] | 3.6 [3.6 – 3.6] |
| Directive : fait ciblé donné | 96 % [96 % – 96 %] | 79 % [79 % – 79 %] | 79 % [79 % – 79 %] |
| Directive : faits nouveaux ajoutés en plus du fait ciblé (~0) | 0.04 [0.04 – 0.04] | 0.14 [0.14 – 0.14] | 0.12 [0.12 – 0.12] |
| Hors scénario : « je sais pas » | 93 % [93 % – 93 %] | 100 % [100 % – 100 %] | 93 % [93 % – 93 %] |
| Suggestion fausse acceptée | 7 % [7 % – 7 %] | 32 % [32 % – 32 %] | 18 % [18 % – 18 %] |
| Écart moyen au taux d'acceptation visé par profil (0) | — | — | — |
| ρ réticence → dévoilement tardif (> 0) | +0.94 [+0.94 – +0.94] | +0.87 [+0.87 – +0.87] | +0.28 [+0.28 – +0.28] |
| ρ suggestibilité → acceptations (> 0) | +0.38 [+0.38 – +0.38] | +0.72 [+0.72 – +0.72] | +0.59 [+0.59 – +0.59] |
| ρ âge → mots par récit (> 0) | +0.48 [+0.48 – +0.48] | +0.73 [+0.73 – +0.73] | +0.72 [+0.72 – +0.72] |
| ρ âge → faits par récit (> 0) | +0.48 [+0.48 – +0.48] | +0.40 [+0.40 – +0.40] | +0.48 [+0.48 – +0.48] |
| Réponses hors rôle par entretien (0) | 0.00 [0.00 – 0.00] | 4.21 [4.21 – 4.21] | 1.64 [1.64 – 1.64] |
| Latence moyenne par tour | 1.7 s [1.7 s – 1.7 s] | 3.5 s [3.5 s – 3.5 s] | 3.7 s [3.7 s – 3.7 s] |

Taux d'acceptation visé par profil (moteur v2, après deux règles de base) : s01 32 %, s02 12 %, s03 5 %, s04 26 %, s05 14 %, s06 5 %, s07 5 %, s08 12 %.

## Par modèle

| Modèle | Condition | Fait central précoce | Faits nouveaux ajoutés / directive | Suggestions acceptées | Écart au visé | ρ réticence | ρ suggestibilité | ρ âge | Replis | Faux détail repris |
|---|---|---|---|---|---|---|---|---|---|---|
| `gemma4:31b` | Hybride | 0 % | 0.04 | 7 % | nan % | +0.94 | +0.38 | +0.48 | 3 | 0/2 |
| `gemma4:31b` | 100 % LLM | 7 % | 0.14 | 32 % | nan % | +0.87 | +0.72 | +0.73 | — | 1/9 |
| `gemma4:31b` | 100 % LLM renforcé | 29 % | 0.12 | 18 % | nan % | +0.28 | +0.59 | +0.72 | — | 5/5 |

ρ : corrélation de Spearman sur les 7 scénarios (n = 7, indicatif) ; « nan » quand une condition ne varie pas (par exemple aucune suggestion acceptée).

## Par scénario (moyenne sur les modèles)

| Scénario | Âge | Réticence | Suggestibilité | Visé | Acceptées Hybride | 1er fait Hybride | Acceptées 100 % LLM | 1er fait 100 % LLM | Acceptées 100 % LLM renforcé | 1er fait 100 % LLM renforcé |
|---|---|---|---|---|---|---|---|---|---|---|
| s01_bagarre_parc | 5 | 0.2 | 0.8 | 32 % | 50 % | 8.0 | 100 % | 8.0 | 75 % | 8.0 |
| s02_violences_maison | 8 | 0.65 | 0.4 | 12 % | 0 % | 11.0 | 0 % | 11.0 | 0 % | 5.5 |
| s03_vol_boulangerie | 11 | 0.1 | 0.2 | 5 % | 0 % | 8.0 | 0 % | 8.0 | 0 % | 8.0 |
| s04_violences_conjugales | 6 | 0.55 | 0.6 | 26 % | 0 % | 9.0 | 75 % | 9.0 | 50 % | 9.0 |
| s05_negligence | 7 | 0.4 | 0.5 | 14 % | 0 % | 9.0 | 50 % | 11.0 | 0 % | 7.5 |
| s06_racket | 10 | 0.45 | 0.25 | 5 % | 0 % | 9.0 | 0 % | 9.0 | 0 % | 8.0 |
| s07_delit_fuite | 12 | 0.05 | 0.15 | 5 % | 0 % | 8.0 | 0 % | 5.0 | 0 % | 6.0 |
| s08_violences_maison_secret | 8 | 0.65 | 0.4 | 12 % | — | — | — | — | — | — |
