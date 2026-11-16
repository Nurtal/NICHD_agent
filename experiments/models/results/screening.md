# Tri des modèles candidats (voix de l'enfant)

7 entretiens hybrides par modèle (un par scénario, graine 0), 23 tours scriptés. Repli = le filtre a rejeté deux mises en mots et le gabarit a répondu.

| Modèle | Famille | Prio. | Sur GPU | Repli | OK du 1er coup | Motifs de rejet | Latence/tour | Mots/réponse | Hors rôle | Mots anglais |
|---|---|---|---|---|---|---|---|---|---|---|
| `gemma4:latest` | gemma | 0 | 100 % | 1.9 % | 98 % | too_long 7 | 0.2 s | 8.9 | 0 | 0 |
| `qwen3.8:latest` | qwen | 0 | 100 % | 3.7 % | 94 % | too_long 8, leak 5, missing 4 | 1.1 s | 9.3 | 0 | 0 |
| `phi4:latest` | phi | 0 | 100 % | 10.6 % | 84 % | too_long 35, leak 7, emoji 2, missing 1 | 0.9 s | 17.8 | 0 | 0 |
| `mistral:latest` | mistral | 0 | 100 % | 12.4 % | 81 % | too_long 27, missing 11, leak 9, contradicts 8 | 0.6 s | 15.7 | 0 | 0 |

Sur GPU < 100 % : une partie du modèle tourne sur le CPU (beaucoup plus lent). Motifs : leak = fait non autorisé, missing = fait autorisé absent, too_long = « je sais pas » qui brode, contradicts = contredit la décision du moteur, emoji, forbidden = lexique interdit.
