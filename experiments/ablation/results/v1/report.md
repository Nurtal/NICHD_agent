# Ablation : enfant hybride vs enfant 100 % LLM

Modèle : `qwen3.8:latest` (local, Ollama), température 0,7, réflexion désactivée. 21 entretiens par condition (7 scénarios × 3 graines), 23 tours scriptés identiques. La condition hybride reçoit les étiquettes NICHD de référence (classifieur hors comparaison) ; la condition 100 % LLM reçoit la fiche complète, le profil, des consignes de comportement et tout l'historique. Mêmes détecteurs textuels (ancres des unités) pour les deux.

## Résultats globaux

| Critère (attendu) | Hybride | 100 % LLM |
|---|---|---|
| Entretiens où un fait central sort avant la transition (attendu : 0) | 0 % | 62 % |
| Mots par réponse aux règles de base (attendu : très court) | 1.4 | 9.8 |
| Question directive : fait ciblé donné | 96 % | 81 % |
| Question directive : autres faits ajoutés (attendu : ~0) | 0.25 | 0.80 |
| Même question directive répétée : réponse cohérente | 100 % | 100 % |
| Question hors scénario : « je sais pas » | 100 % | 100 % |
| Suggestion fausse acceptée | 31 % | 0 % |
| Faux détail accepté puis repris au rappel libre | 2/13 | 0/0 |
| Réponses contenant un terme du lexique interdit (total) | 0 | 0 |
| Réponses vides (total) | 0 | 0 |
| Latence moyenne par tour | 1.4 s | 2.5 s |

Réponses de repli de la condition hybride (filtre de sortie) : 14.

## Le profil de l'enfant est-il respecté ?

Corrélation de Spearman sur les 7 scénarios (n = 7, indicatif) entre un paramètre du profil et le comportement observé.

| Scénario | Âge | Réticence | Suggestibilité | 1er fait (tour) Hybride | Suggestions acceptées Hybride | Mots / invitation Hybride | 1er fait (tour) 100 % LLM | Suggestions acceptées 100 % LLM | Mots / invitation 100 % LLM |
|---|---|---|---|---|---|---|---|---|---|
| s01_bagarre_parc | 5 | 0.2 | 0.8 | 8.0 | 50 % | 15 | 2.0 | 0 % | 14 |
| s02_violences_maison | 8 | 0.65 | 0.4 | 11.0 | 17 % | 26 | 6.3 | 0 % | 37 |
| s03_vol_boulangerie | 11 | 0.1 | 0.2 | 8.0 | 17 % | 19 | 5.3 | 0 % | 40 |
| s04_violences_conjugales | 6 | 0.55 | 0.6 | 11.0 | 50 % | 9 | 8.0 | 0 % | 13 |
| s05_negligence | 7 | 0.4 | 0.5 | 9.0 | 50 % | 36 | 2.0 | 0 % | 32 |
| s06_racket | 10 | 0.45 | 0.25 | 9.0 | 17 % | 37 | 6.7 | 0 % | 54 |
| s07_delit_fuite | 12 | 0.05 | 0.15 | 8.0 | 17 % | 24 | 7.7 | 0 % | 42 |

| Lien attendu | Hybride | 100 % LLM |
|---|---|---|
| Réticence ↗ → dévoilement plus tardif (ρ > 0) | +0.94 | +0.20 |
| Suggestibilité ↗ → plus d'acceptations (ρ > 0) | +0.87 | +nan |
| Âge ↗ → récits plus longs (ρ > 0) | +0.39 | +0.86 |
