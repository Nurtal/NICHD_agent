# Ablation : enfant hybride vs enfant 100 % LLM

*v2, 13 novembre 2026. Code : `experiments/ablation/` (protocole, exécution, analyse). Transcriptions : `experiments/ablation/results/transcripts.jsonl`. Tableaux générés, dont le détail par modèle et par scénario : `experiments/ablation/results/report.md`. La v1 (un seul modèle, ancienne calibration) est archivée dans `results/v1/`.*

## Question

Le découplage « moteur de comportement déterministe + LLM limité à la mise en mots » apporte-t-il quelque chose par rapport à un enfant simulé entièrement par le LLM, à qui l'on donne toute la fiche du scénario et des consignes de comportement ? Et la réponse tient-elle quand on change de modèle et qu'on renforce le témoin ?

## Dispositif

- **4 modèles open source, tous locaux** (Ollama, 2 × TITAN RTX) : `qwen3.8` (27 B), `phi4` (14 B), `gemma4` (8 B), `mistral` (7 B). Température 0,7, sans réflexion.
- **Mêmes entretiens scriptés** : 23 tours identiques par scénario (rapport, règles de base, pratique narrative, transition, invitations, 3 questions directives dont une répétée, 2 questions sur des détails absents de la fiche, 2 suggestions fausses, rappel libre, clôture). 7 scénarios × 3 graines × 4 modèles = **84 entretiens par condition**, 252 au total, 5 796 réponses.
- **Trois conditions** :
  - **Hybride** : notre simulateur (moteur v2, calibré sur la littérature), piloté par les étiquettes NICHD de référence. Le classifieur est donc hors comparaison : on ne compare que l'enfant.
  - **100 % LLM** : il reçoit la fiche complète (tous les faits), l'événement neutre, le profil (en chiffres et en mots), des consignes explicites (« tu ne parles de l'événement que si on t'y invite… un enfant suggestible peut dire oui à une suggestion fausse… »), le registre de langue par âge et **tout** l'historique.
  - **100 % LLM renforcé** : comme le précédent, plus des exemples few-shot d'un autre scénario, le **taux d'acceptation des suggestions visé** pour ce profil (le même que celui du moteur) et un rappel de la consigne à chaque tour.
- **Même environnement d'exécution** pour toutes les conditions : séquences d'arrêt (« Adulte : », « Toi : »…) et plafond de 400 jetons. Sans cela, `phi4` et `mistral` écrivaient parfois la suite du dialogue à la place de l'interviewer, jusqu'à 4 000 mots.
- **Mêmes détecteurs** pour toutes les conditions : faits repérés par les ancres de la fiche, en ignorant celles présentes dans l'événement neutre. Les détecteurs ont été vérifiés à la main sur des échantillons de chaque modèle. L'acceptation des suggestions est juste dans 13 cas sur 14 et le quatorzième est ambigu. Pour les faits sortis trop tôt, 6 détections sur 8 sont justes. Les 2 erreurs viennent d'ancres fragiles (« souvent », « gymnase ») et ne concernent que 4 entretiens sur 103.

## Résultats

Moyenne sur les 4 modèles, avec [min – max] entre modèles.

| Critère (attendu) | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Entretiens où un fait central sort avant la transition (0 %) | **0 %** [0 – 0] | 68 % [24 – 100] | 55 % [10 – 95] |
| Mots par réponse aux règles de base (très peu) | **2,8** [1,3 – 4,4] | 11,8 [9,7 – 14,3] | 8,6 [3,8 – 15,0] |
| Directive : fait ciblé donné | **96 %** [96 – 96] | 86 % [81 – 92] | 82 % [77 – 86] |
| Directive : faits nouveaux ajoutés en plus du fait ciblé (~0) | **0,04** | 0,13 [0,02 – 0,29] | 0,14 [0,06 – 0,23] |
| Hors scénario : « je sais pas » | 84 % [60 – 98] | 83 % [67 – 100] | 74 % [45 – 100] |
| Suggestion fausse acceptée | 16 % [14 – 17] | 3 % [0 – 7] | 22 % [10 – 43] |
| Écart moyen au taux d'acceptation visé par profil (0) | **7 %** [7 – 8] | 13 % [11 – 14] | 17 % [9 – 32] |
| Réponses hors rôle par entretien (0) | 0,02 | 0,00 | 0,55 [0 – 2,2] |
| Latence moyenne par tour | 0,9 s | 1,9 s | 1,3 s |

**Le profil est-il respecté ?** Corrélation de Spearman sur les 7 scénarios (n = 7 : indicatif).

| Lien attendu | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Réticence plus forte → premier fait central plus tardif | **+0,94** [+0,94 – +0,94] | +0,00 [−0,18 – +0,20] | +0,18 [−0,10 – +0,77] |
| Suggestibilité plus forte → plus de suggestions acceptées | **+0,92** [+0,81 – +0,95] | +0,20 (souvent non calculable : 0 acceptation) | +0,87 [+0,80 – +0,97] |
| Âge plus élevé → récits plus longs (mots) | +0,77 [+0,68 – +0,89] | +0,78 [+0,68 – +0,89] | +0,60 [+0,04 – +0,93] |
| Âge plus élevé → plus de faits par récit | **+0,86** [+0,81 – +0,93] | +0,69 [+0,40 – +0,93] | +0,70 [+0,64 – +0,79] |

## Lecture

1. **Le résultat principal se réplique sur 4 modèles.** L'hybride ne laisse sortir aucun fait central avant la transition, avec tous les modèles. Le LLM seul en laisse sortir dans 24 % (`gemma4`) à 100 % (`mistral`) des entretiens, et le témoin renforcé dans 10 % à 95 %. Les exemples, le taux visé et le rappel à chaque tour réduisent le problème avec les modèles les plus forts, sans le supprimer. Ils n'y changent presque rien avec les plus faibles (`phi4` 86 %, `mistral` 95 %).
2. **Le comportement de l'hybride ne dépend pas du modèle.** Les décisions viennent du moteur, si bien que les métriques comportementales sont identiques d'un modèle à l'autre : 0 % de faits précoces, 96 % de directives atteintes, 14–17 % de suggestions acceptées, ρ réticence = +0,94 partout. Chez le LLM seul, les mêmes critères varient d'un facteur 4 selon le modèle. Pour un outil de formation, c'est la reproductibilité qui compte : deux apprenants doivent rencontrer le même enfant.
3. **Renforcer le témoin rend la suggestibilité contrôlable, mais pas la réticence.** Quand on lui donne le taux visé, le LLM accepte davantage les suggestions chez les profils suggestibles (ρ = +0,87). Le niveau, lui, reste mal tenu (écart moyen au taux visé de 17 %, contre 7 % pour l'hybride). `gemma4` accepte 43 % des suggestions en moyenne et 18 faux détails, sans jamais en reprendre un seul au rappel. Ces acquiescements ne laissent pas de trace dans la suite de l'entretien. La réticence, elle, n'est respectée par aucun témoin (ρ entre −0,10 et +0,77 selon le modèle).
4. **Le LLM seul reste un témoin presque infaillible.** Sans taux visé, il accepte 3 % des suggestions fausses, même pour Léo (5 ans, suggestibilité 0,8), et corrige l'adulte avec assurance. Côté hybride, les acceptations suivent le profil et les faux détails acceptés reviennent parfois d'eux-mêmes au rappel (11 fois sur 27). C'est précisément la contamination que l'entraînement NICHD doit apprendre à éviter.
5. **Effet de l'âge : l'artefact de la v1 est corrigé.** La v1 donnait un ρ âge de +0,39 pour l'hybride. Cela venait d'une métrique qui moyennait aussi les invitations sans contenu. En mesurant les seules invitations productives, l'hybride fait aussi bien que le LLM seul sur la longueur (+0,77 contre +0,78) et mieux sur le nombre de faits (+0,86 contre +0,69).
6. **Le LLM seul sort de son rôle.** Même avec les séquences d'arrêt, le témoin renforcé produit en moyenne 0,55 réponse hors rôle par entretien (jusqu'à 2,2 avec `phi4`) : emojis, didascalies entre parenthèses, « Si tu as d'autres questions, n'hésite pas ! ». L'hybride en produit 0,02 (deux « merci 😊 » de `phi4` à la clôture).

## Ce que la réplication a révélé côté hybride, et ce qui a été corrigé

- **Une mise en mots peut contredire la décision du moteur.** `mistral` rendait des refus décidés par le moteur par « Oui, elle avait un couteau » ou « Ben oui, papa avait bu de l'alcool ». Le filtre de sortie ne vérifiait que le contenu, pas le sens de la réponse : l'hybride acceptait alors 68 % des suggestions au lieu de 17 %. Le filtre rejette désormais un « oui » quand le moteur a décidé « non », et un « non » quand il a décidé d'acquiescer ; c'est alors le gabarit qui répond. Après correction, `mistral` donne exactement les mêmes acceptations que les autres modèles. Les données d'avant correction sont archivées dans `results/v2-pre-fix/`.
- **Le coût du filet de sécurité dépend du modèle.** Le gabarit remplace la réponse du LLM dans 2 % des tours avec `gemma4` et `qwen3.8`, mais dans 11 à 12 % avec `phi4` et `mistral` (139 sur 1 932 au total). Les rejets portent surtout sur les « je sais pas » et les « d'accord » que le LLM enjolive. Le comportement prévu est préservé, mais la variété des réponses en souffre. Le modèle par défaut doit donc rester un modèle qui obéit bien à la consigne de mise en mots.
- **Réponse « Non, c'est tout » à une suggestion** (signalé en v1) : la consigne de l'acte `deny` demande maintenant un simple « non ».
- **Calibration** (signalée en v1) : le biais « oui » et le taux d'acquiescement ont été réduits d'après la littérature (Fritzley & Lee 2003 ; Okanda & Itakura 2010 ; voir `docs/research/revue-litterature.md`). Les taux observés suivent la cible (écart moyen de 7 %). Avec seulement 6 suggestions par profil et par modèle, le taux observé par scénario reste bruité, par exemple 50 % observés pour 32 % visés chez Léo.

## Limites

- Interviewer scripté et non adaptatif. 7 scénarios, si bien que les corrélations (n = 7) sont indicatives. Seulement 2 suggestions et 2 questions hors scénario par entretien.
- Modèles de 7 à 27 B quantifiés, sans réflexion. Un modèle plus gros, ou avec réflexion, pourrait mieux tenir la réticence en condition LLM seul. La conclusion reste « avec ces modèles et ces consignes ».
- La détection des faits par ancres est lexicale : vérifiée sur échantillon, pas exhaustivement.
- Les emojis passent encore le filtre de l'hybride (2 cas). Le réalisme perçu n'est pas mesuré : il demande un jugement en aveugle par des formateurs NICHD.

## Reproduire

```bash
uv run python experiments/ablation/run.py --models qwen3.8:latest phi4:latest gemma4:latest mistral:latest --seeds 0 1 2
#   ~2 h sur 2 × TITAN RTX, reprend là où il s'est arrêté ; décharge chaque modèle avant le suivant
uv run python experiments/ablation/analyze.py -o experiments/ablation/results/report.md
```
