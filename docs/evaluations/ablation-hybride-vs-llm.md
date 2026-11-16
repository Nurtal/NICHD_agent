# Ablation : enfant hybride vs enfant 100 % LLM

*v3, 16 novembre 2026 (8 modèles ; la v2 du 13/11 en comptait 4). Code : `experiments/ablation/` (protocole, exécution, analyse). Transcriptions : `experiments/ablation/results/transcripts.jsonl`. Tableaux générés, dont le détail par modèle et par scénario : `experiments/ablation/results/report.md`. La v1 (un seul modèle, ancienne calibration) est archivée dans `results/v1/`.*

## Question

Le découplage « moteur de comportement déterministe + LLM limité à la mise en mots » apporte-t-il quelque chose par rapport à un enfant simulé entièrement par le LLM, à qui l'on donne toute la fiche du scénario et des consignes de comportement ? Et la réponse tient-elle quand on change de modèle, de famille et de taille, et qu'on renforce le témoin ?

## Dispositif

- **8 modèles open source, tous locaux** (Ollama, 2 × TITAN RTX), 6 familles :
  - v2 : `qwen3.8` (27 B), `phi4` (14 B), `gemma4` (variante E4B : 8 B paramètres, 4 B effectifs), `mistral` (7 B) ;
  - ajoutés en v3 (priorité 1 de `docs/research/modeles-candidats.md`) : `mistral-small3.2` (24 B), `gemma4:31b`, `gpt-oss:20b` (réflexion au niveau `low`, impossible à couper), `olmo-3.1:32b-instruct`.

  Température 0,7, sans réflexion (sauf `gpt-oss`).
- **Mêmes entretiens scriptés** : 23 tours identiques par scénario (rapport, règles de base, pratique narrative, transition, invitations, 3 questions directives dont une répétée, 2 questions sur des détails absents de la fiche, 2 suggestions fausses, rappel libre, clôture). 7 scénarios × 3 graines × 8 modèles = **168 entretiens par condition**, 504 au total, 11 592 réponses.
- **Trois conditions** :
  - **Hybride** : notre simulateur (moteur v2, calibré sur la littérature), piloté par les étiquettes NICHD de référence. Le classifieur est donc hors comparaison : on ne compare que l'enfant.
  - **100 % LLM** : il reçoit la fiche complète (tous les faits), l'événement neutre, le profil (en chiffres et en mots), des consignes explicites (« tu ne parles de l'événement que si on t'y invite… un enfant suggestible peut dire oui à une suggestion fausse… »), le registre de langue par âge et **tout** l'historique.
  - **100 % LLM renforcé** : comme le précédent, plus des exemples few-shot d'un autre scénario, le **taux d'acceptation des suggestions visé** pour ce profil (le même que celui du moteur) et un rappel de la consigne à chaque tour.
- **Même environnement d'exécution** pour toutes les conditions : séquences d'arrêt (« Adulte : », « Toi : »…) et plafond de 400 jetons. Sans cela, `phi4` et `mistral` écrivaient parfois la suite du dialogue à la place de l'interviewer, jusqu'à 4 000 mots.
- **Mêmes détecteurs** pour toutes les conditions : faits repérés par les ancres de la fiche, en ignorant celles présentes dans l'événement neutre. En v2, vérification à la main sur des échantillons de chaque modèle : l'acceptation des suggestions est juste dans 13 cas sur 14 (le quatorzième est ambigu) ; pour les faits sortis trop tôt, 6 détections sur 8 sont justes (2 ancres fragiles, « souvent » et « gymnase », sur 4 entretiens sur 103). En v3, les 13 acceptations détectées pour `gemma4:31b` seul sont toutes justes. Le détecteur de sortie de rôle compte désormais aussi les didascalies entre astérisques (`*Emma regarde ses chaussures*`), fréquentes chez `gemma4:31b`.

## Résultats

Moyenne sur les 8 modèles, avec [min – max] entre modèles.

| Critère (attendu) | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Entretiens où un fait central sort avant la transition (0 %) | **0 %** [0 – 0] | 55 % [10 – 100] | 46 % [10 – 95] |
| Mots par réponse aux règles de base (très peu) | **2,3** [1,0 – 4,4] | 8,6 [4,0 – 14,3] | 6,1 [2,4 – 15,0] |
| Directive : fait ciblé donné | **96 %** [96 – 96] | 81 % [71 – 92] | 78 % [67 – 86] |
| Directive : faits nouveaux ajoutés en plus du fait ciblé (~0) | **0,04** | 0,14 [0,02 – 0,29] | 0,14 [0,06 – 0,23] |
| Hors scénario : « je sais pas » | 89 % [60 – 100] | 87 % [67 – 100] | 80 % [45 – 100] |
| Suggestion fausse acceptée | 16 % [14 – 17] | 9 % [0 – 31] | 19 % [0 – 43] |
| Écart moyen au taux d'acceptation visé par profil (0) | **7 %** [7 – 8] | 16 % [11 – 25] | 17 % [9 – 32] |
| Réponses hors rôle par entretien (0) | **0,01** [0 – 0,10] | 0,58 [0 – 4,2] | 0,67 [0 – 2,4] |
| Latence moyenne par tour | 1,2 s [0,4 – 2,2] | 2,0 s [0,4 – 5,1] | 1,6 s [0,3 – 3,7] |

**Le profil est-il respecté ?** Corrélation de Spearman sur les 7 scénarios (n = 7 : indicatif).

| Lien attendu | Hybride | 100 % LLM | 100 % LLM renforcé |
|---|---|---|---|
| Réticence plus forte → premier fait central plus tardif | **+0,94** [+0,94 – +0,94] | +0,19 [−0,18 – +0,88] | +0,33 [−0,10 – +0,77] |
| Suggestibilité plus forte → plus de suggestions acceptées | **+0,94** [+0,81 – +0,95] | +0,56 (souvent non calculable : 0 acceptation) | +0,85 [+0,80 – +0,97] |
| Âge plus élevé → récits plus longs (mots) | +0,72 [+0,61 – +0,89] | +0,77 [+0,54 – +0,93] | +0,69 [+0,04 – +0,93] |
| Âge plus élevé → plus de faits par récit | **+0,82** [+0,59 – +0,93] | +0,65 [+0,40 – +0,93] | +0,71 [+0,57 – +0,93] |

**Faits centraux sortis avant la transition, par modèle** (LLM seul / renforcé) : `gemma4:31b` 10 % / 19 %, `gemma4` E4B 24 % / 10 %, `mistral-small3.2` 33 % / 14 %, `gpt-oss:20b` 52 % / 62 %, `qwen3.8` 62 % / 29 %, `olmo-3.1:32b` 71 % / 52 %, `phi4` 86 % / 86 %, `mistral` 7B 100 % / 95 %. Hybride : 0 % pour les 8.

## Lecture

1. **Le résultat principal se réplique sur 8 modèles et 6 familles.** L'hybride ne laisse sortir aucun fait central avant la transition, avec tous les modèles. Le LLM seul en laisse sortir dans 10 % à 100 % des entretiens selon le modèle, et le témoin renforcé dans 10 % à 95 %. Les exemples, le taux visé et le rappel à chaque tour aident certains modèles (`qwen3.8` de 62 à 29 %, `mistral-small3.2` de 33 à 14 %), n'en aident pas d'autres (`phi4`) et en dégradent un (`gpt-oss` de 52 à 62 %).
2. **Le comportement de l'hybride ne dépend pas du modèle.** Les décisions viennent du moteur, si bien que les métriques comportementales sont identiques d'un modèle à l'autre : 0 % de faits précoces, 96 % de directives atteintes, 14–17 % de suggestions acceptées, ρ réticence = +0,94 partout. Chez le LLM seul, les mêmes critères varient d'un facteur 10 selon le modèle. Pour un outil de formation, c'est la reproductibilité qui compte : deux apprenants doivent rencontrer le même enfant.
3. **Un modèle plus gros peut presque tenir la réticence, mais pas de façon fiable.** `gemma4:31b` seul est le seul témoin qui approche l'hybride sur la réticence : 10 % de faits précoces, ρ réticence +0,88, ρ suggestibilité +0,91. Ce n'est pas un effet général de la taille : `olmo-3.1:32b` (71 %) et `qwen3.8` 27 B (62 %) font moins bien que `gemma4` E4B (24 %). Ce bon résultat est aussi fragile et coûteux :
   - **instable selon la consigne** : avec le prompt renforcé, le même modèle passe à 19 % de faits précoces et ρ réticence +0,20 ;
   - **mal calibré** : il accepte 31 % des suggestions fausses en moyenne, toutes chez les profils suggestibles, mais trop souvent (100 % des suggestions chez Léo, pour 32 % visés). Son écart au taux visé est de 25 %, contre 7 % pour l'hybride ;
   - **hors rôle** : 18 % de ses réponses contiennent des didascalies (`*Emma baisse la tête et tripote son t-shirt*`), soit 4,2 par entretien. Elles s'afficheraient telles quelles devant l'apprenant.
4. **Renforcer le témoin rend la suggestibilité mieux ordonnée, mais pas mieux dosée.** Avec le taux visé, le LLM accepte davantage chez les profils suggestibles (ρ = +0,85), mais le niveau reste mal tenu (écart moyen de 17 %, contre 7 % pour l'hybride). `gemma4` E4B accepte 43 % des suggestions et 18 faux détails, sans en reprendre un seul au rappel. Ces acquiescements ne laissent pas de trace dans la suite de l'entretien.
5. **Le LLM seul reste souvent un témoin presque infaillible.** Sans taux visé, 4 modèles sur 8 n'acceptent aucune suggestion fausse, même pour Léo (5 ans, suggestibilité 0,8), et corrigent l'adulte avec assurance. Côté hybride, les acceptations suivent le profil et les faux détails acceptés reviennent parfois d'eux-mêmes au rappel (20 fois sur 55). C'est précisément la contamination que l'entraînement NICHD doit apprendre à éviter.
6. **Effet de l'âge.** L'hybride suit l'âge sur le nombre de faits par récit (+0,82, contre +0,65 pour le LLM seul) et à peu près sur la longueur (+0,72 contre +0,77). L'artefact de la v1 (+0,39), dû à une métrique qui moyennait les invitations sans contenu, reste corrigé.
7. **Le LLM seul sort de son rôle.** Même avec les séquences d'arrêt, le LLM seul produit en moyenne 0,6 à 0,7 réponse hors rôle par entretien : didascalies, emojis, « Si tu as d'autres questions, n'hésite pas ! ». L'hybride en produit 0,01 (deux « merci 😊 » de `phi4` à la clôture, avant que le filtre ne rejette les emojis).

## Ce que la réplication a révélé côté hybride, et ce qui a été corrigé

- **Une mise en mots peut contredire la décision du moteur.** `mistral` rendait des refus décidés par le moteur par « Oui, elle avait un couteau » ou « Ben oui, papa avait bu de l'alcool ». Le filtre de sortie ne vérifiait que le contenu, pas le sens de la réponse : l'hybride acceptait alors 68 % des suggestions au lieu de 17 %. Le filtre rejette désormais un « oui » quand le moteur a décidé « non », et un « non » quand il a décidé d'acquiescer ; c'est alors le gabarit qui répond. Après correction, `mistral` donne exactement les mêmes acceptations que les autres modèles. Les données d'avant correction sont archivées dans `results/v2-pre-fix/`.
- **Le coût du filet de sécurité dépend du modèle.** Le gabarit remplace la réponse du LLM dans 189 tours sur 3 864 (4,9 %) : 3 pour `gpt-oss:20b`, 7 pour `gemma4:31b`, 10 pour `gemma4` E4B, 16 pour `qwen3.8`, 17 pour `olmo-3.1:32b`, 23 pour `mistral-small3.2`, mais 55 pour `phi4` et 58 pour `mistral` 7B (11–12 %). Les rejets portent surtout sur les « je sais pas » et les « d'accord » que le LLM enjolive. Le comportement prévu est préservé, mais la variété des réponses en souffre. Le modèle par défaut doit donc rester un modèle qui obéit bien à la consigne de mise en mots : les 4 nouveaux candidats le font tous.
- **Réponse « Non, c'est tout » à une suggestion** (signalé en v1) : la consigne de l'acte `deny` demande maintenant un simple « non ».
- **Calibration** (signalée en v1) : le biais « oui » et le taux d'acquiescement ont été réduits d'après la littérature (Fritzley & Lee 2003 ; Okanda & Itakura 2010 ; voir `docs/research/revue-litterature.md`). Les taux observés suivent la cible (écart moyen de 7 %). Avec seulement 6 suggestions par profil et par modèle, le taux observé par scénario reste bruité, par exemple 50 % observés pour 32 % visés chez Léo.

## Limites

- Interviewer scripté et non adaptatif. 7 scénarios, si bien que les corrélations (n = 7) sont indicatives. Seulement 2 suggestions et 2 questions hors scénario par entretien.
- Modèles de 7 à 32 B quantifiés, sans réflexion (sauf `gpt-oss`, au niveau bas). `gemma4:31b` montre qu'un modèle peut presque tenir la réticence seul. Un modèle plus gros (`llama3.3:70b`, priorité 2) reste à tester. La conclusion reste « avec ces modèles et ces consignes ».
- La détection des faits par ancres est lexicale : vérifiée sur échantillon, pas exhaustivement.
- Le réalisme perçu n'est pas mesuré : il demande un jugement en aveugle par des formateurs NICHD. En lisant des extraits, `gemma4:31b` produit le français le plus naturel en hybride, alors que `gpt-oss` et `olmo` recopient souvent la fiche sans ponctuation.

## Reproduire

```bash
uv run python experiments/ablation/run.py --config experiments/models/candidates.yaml \
  --models qwen3.8:latest phi4:latest gemma4:latest mistral:latest \
           mistral-small3.2:24b gemma4:31b gpt-oss:20b olmo-3.1:32b-instruct --seeds 0 1 2
#   ~2 h pour les 4 modèles v2, ~3 h pour les 4 modèles v3 sur 2 × TITAN RTX ;
#   reprend là où il s'est arrêté ; décharge chaque modèle avant le suivant
uv run python experiments/ablation/analyze.py -o experiments/ablation/results/report.md
```
