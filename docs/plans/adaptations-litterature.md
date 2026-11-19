# Plan d'implémentation : adaptations issues de la littérature

*Novembre 2026. Ce plan met en œuvre les pistes A1 à A15 de la
[confrontation du modèle à la littérature](../research/confrontation-modele-litterature.md). Chaque lot correspond à
une PR, fusionnée sur le « merge » de l'utilisateur. Les valeurs nouvelles sont `estimated` et sont à faire relire par
un formateur NICHD, en priorité A1, A3 et A10.*

## Contexte

La confrontation a montré que le moteur ignore trois choses documentées.
- **La réaction de l'interviewer** : la réticence remonte quand l'interviewer rejette un « je sais pas » ou un déni.
- **Le coût de la pression** : une question suggestive ou à choix fait se fermer un enfant réticent.
- **La répétition des questions** : l'enfant change de réponse ou invente.

Il ignore aussi des formes de question que le protocole distingue : invitation par segment de temps, « Est-ce que tu te
souviens… ? », promesse de dire la vérité, pratique épisodique.

Le but est un enfant simulé dont les réactions suivent ces régularités. Les garde-fous des ADR 0001 à 0004 sont
conservés :
- le LLM ne décide rien ;
- le corps ne porte aucune signature du mensonge ;
- le suivi de l'apprenant ne fuit aucune information ;
- les journaux existants se rejouent.

## Contraintes transverses

### Rejeu des anciens journaux

Le rejeu charge aujourd'hui les valeurs par défaut **actuelles**, puis applique les paramètres enregistrés dans le
journal (`replay.py`, `Parameters.load(..., overrides=log.parameters)`). Un paramètre nouveau, absent d'un ancien
journal, prendrait donc sa valeur active, et les décisions des 21 journaux du MVP changeraient.

Mécanisme proposé (lot 0) :
- le format de journal passe à 4 ;
- chaque paramètre nouveau déclare dans `parameters.yaml` une **valeur neutre** (`neutral:`), qui désactive sa règle ;
- au rejeu d'un journal de format inférieur à 4, les paramètres absents du journal prennent leur valeur neutre, et les
  champs nouveaux du classifieur sont absents, donc sans effet ;
- `test_mvp_logs_replay_identically` reste vert à chaque lot. C'est le critère de non-régression principal.

### Flux aléatoires

- Un tirage nouveau ne doit jamais décaler les flux existants.
- Les règles qui touchent les décisions tirent dans un flux dédié, `Random(f"{seed}:dynamics")`.
- Les règles qui touchent le corps tirent dans `{seed}:demeanor`, comme aujourd'hui (ADR 0002 §3).

### Classifieur

Les champs nouveaux arrivent tous dans une seule version du skill (0.3.0, lot 2), pour ne mesurer le κ qu'une fois.
- Les cas nouveaux vont dans `skill/testset.jsonl`, en plus de quelques exemples dans `examples.jsonl`, disjoints du jeu
  de test comme aujourd'hui.
- Le κ global du jeu existant ne doit pas baisser de plus de 0,02.

### Suivi de l'apprenant (ADR 0004)

Les alertes nouvelles ne dépendent que de ce que l'apprenant a dit et de ce que l'enfant a dit au tour précédent, ce
que l'apprenant a entendu. Elles ne révèlent jamais un fait, un mensonge ou une cause.

## Outil de mesure (lot 0)

`experiments/fidelity/` simule des entretiens scriptés sur 100 seeds, avec le classifieur manuel (`classifiers/manual.py`),
donc sans LLM et rapidement. Il produit une mesure par piste :

| Piste | Mesure | Cible |
|---|---|---|
| A1 | unités vraies après un « je sais pas » accepté, comparées à un « je sais pas » rejeté ; taux d'acquiescement après un rejet | acceptation > rejet ; rejet ⇒ acquiescement en hausse |
| A2 | taux de changement de réponse et d'invention selon le nombre de répétitions | > 25 % de changements ; invention croissante (Krähenbühl et al., 2009) |
| A3 | probabilité de dévoiler par invitations + soutien, comparée à des suggestives répétées, sur un enfant réticent | invitations > suggestives |
| A5 | taux de « oui » sans détail par bande d'âge | décroissant avec l'âge, de l'ordre de 15 à 45 % chez les plus jeunes |
| A6, A7 | taux d'acquiescement selon le soutien, et selon la règle énoncée ou pratiquée | soutien et pratique ⇒ baisse |
| A8, A9 | part des faits protégés révélés avec ou sans promesse ; fuites par âge ; répartition omission/déni | promesse ⇒ hausse ; fuites décroissantes avec l'âge ; omissions > dénis |
| A10, A11 | signes d'émotion après soutien à activation égale ; activation avant le dévoilement | soutien ⇒ plus de signes ; hausse avant dévoilement |

Le rapport est écrit dans `docs/evaluations/fidelite.md` et mis à jour à chaque lot.

## Lots

### Lot 0 : socle (PR 1)

1. Format de journal 4. Champ `neutral` dans `parameters.yaml`. Résolution des valeurs neutres au rejeu des anciens
   journaux (`parameters.py`, `replay.py`).
2. Flux `{seed}:dynamics`.
3. Mémoire d'interaction dans l'état du moteur (`engine.py`, `EngineState`) :
   - dernier acte de l'enfant et cible du dernier tour ;
   - compteur de questions fermées par clé `(cible, proposition)`. Une cible hors scénario prend pour clé le texte
     normalisé de la question.
4. `experiments/fidelity/` et un premier rapport de référence, avant toute adaptation.

Ce lot ne change aucun comportement. Tests : rejeu du MVP identique, et rejeu d'un journal de format 3 avec ses valeurs
neutres.

### Lot 1 : dynamique de la réticence, moteur seul (PR 2)

Aucun changement du classifieur.

- **A3, coût de la pression.** Une suggestive ou une question à choix sur l'événement cible, avant le dévoilement, fait
  monter la réticence :
  - `pressure_reluctance_rise` × réticence courante ;
  - `disclosure_pressure` est recalibré pour que les invitations restent, en moyenne, le chemin le plus sûr ;
  - valeur neutre : 0.
- **A6, soutien et acquiescement.** `support_acquiescence_drop`, avec un plafond comme pour les règles de base. Valeur
  neutre : 0.
- **A1, réaction au « je sais pas » et au déni.** Si l'acte précédent de l'enfant était `dont_know`, `reluctant` ou un
  déni :
  - **acceptation** (soutien, facilitateur, autre sujet) : `acceptance_reluctance_drop` ;
  - **rejet** (même cible reposée, surtout en question fermée ou suggestive) : `rejection_reluctance_rise`, plus
    `rejection_acquiescence_boost` pour ce tour, qui produit la réponse de complaisance ;
  - valeurs neutres : 0.
- **A2, répétition.** À partir de la 2ᵉ occurrence d'une même clé fermée :
  - `p_change_on_repeat` : l'enfant abandonne une réponse **devinée**. Un fait vrai déjà dit reste plus stable,
    `repeat_true_stability` ;
  - `p_confabulation` est multiplié par `repeat_confabulation_gain` puissance (n − 1) ;
  - valeurs neutres : 0 et 1.
- **Suivi (`coaching.py`).** Alertes « je ne sais pas rejeté » et « question répétée », avec un conseil fixe. Le barème
  reste à valider par un formateur.
- **Réticence ↔ activation.** La base d'activation suit désormais la réticence courante, et non plus seulement la
  réticence initiale. Valeur neutre : comportement actuel.

Tests unitaires par règle (`test_phase_effects_disclosure.py`, `test_suggestion_contamination.py`), rejeu du MVP, rapport
de fidélité.

### Lot 2 : classifieur, skill 0.3.0 (PR 3)

Champs ajoutés à `Classification` et au `schema.json` du skill. Tous sont facultatifs ; leur absence vaut le
comportement actuel.

| Champ | Valeurs | Pour |
|---|---|---|
| `segment_hint` | `before` / `during` / `after` / null | A4 : « raconte-moi la fin », « ce qui s'est passé avant » |
| `knowledge_question` | booléen | A5 : « Est-ce que tu sais / te souviens… ? » qui demande implicitement une information |
| `ground_rule_kind` | `dont_know`, `dont_understand`, `correct_me`, `promise`, `practice` | A7 (règle énoncée ou pratiquée), A8 (promesse) |
| `practice_kind` | `episodic` / `generic` | A13 |
| `causal` | booléen | A15 : question ouverte en « pourquoi » ou « comment ça se fait » |

Le moteur consomme ces champs :
- **A4** : `_cued_invitation` prend le pool du segment de l'indice, avant de se rabattre sur l'unité citée.
- **A5** : `knowledge_question` donne un « oui » sans unité avec `p_unelaborated_yes` par bande, sinon le traitement
  d'une directive. Valeur neutre : 0.
- **A7** : une règle énoncée vaut `ground_rule_stated_factor` × l'effet ; une règle pratiquée vaut l'effet plein, ajusté
  par `ground_rule_age_factor`. Valeurs neutres : 1.
- **A13** : le gain de verbosité ne vaut que pour la pratique épisodique (valeur neutre : les deux comptent).
- **A15** : invariant du moteur. Une question `causal` ne reçoit jamais d'acte oui/non ; à défaut d'unité, c'est un
  « je sais pas ».

Le réalisateur (`realization.py`) reçoit le « oui » sans détail comme un acte bref, avec le même filtre de sortie.

Évaluation : 30 à 40 énoncés nouveaux dans le jeu de test, κ global et rappel par champ. Le défaut des démos
(« Raconte-moi la fin ») devient un test de non-régression.

### Lot 3 : mensonge (PR 4)

Ce lot ne concerne que les scénarios avec dissimulation (s08). Les autres scénarios ne bougent pas.

- **A8, promesse.** `ground_rule_kind = promise` fait baisser `concealment` de `promise_concealment_drop`, sans effet sur
  la confabulation. Valeur neutre : 0.
- **A9, omission avant déni.**
  - Mesurer d'abord la répartition simulée. Le moteur fait déjà omettre aux invitations et nier aux questions
    focalisées (`_narrate`, `_lie_to_focused`).
  - Ajuster seulement si l'écart avec Talwar et al. (2004) est net.
- **A9, cohérence selon l'âge.** `p_leak` par bande : sur une question de suite à propos d'un fait protégé déjà couvert
  par un mensonge, l'enfant laisse échapper une unité vraie qui le contredit.
  - C'est un nouvel acte `leak`, journalisé avec le mensonge qu'il contredit.
  - Le suivi le montre au bilan seulement (ADR 0004).
  - Valeur neutre : 0.
- **Avenant à l'ADR 0002.** La fuite est un contenu verbal décidé par le moteur. Elle ne change pas la diction : les
  paires contrôlées mensonge/vérité restent identiques.

### Lot 4 : corps (PR 5)

- **Avenant à l'ADR 0003.**
- **A10, deux variables distinctes.** L'activation reste l'état intérieur. L'expressivité (0–1) indique ce que l'enfant
  ose montrer :
  - le soutien et le rapport font monter l'expressivité ;
  - elle multiplie le gain moteur des signes d'émotion : pleurs, tremblement, crispation ;
  - le désengagement (repli, regard fuyant) suit aussi la réticence, avec `withdrawal_reluctance_weight`.
- **A11, le corps annonce le dévoilement.** Quand la pression dépasse une fraction du seuil sans l'atteindre,
  l'activation monte de `pre_disclosure_rise`. Le mécanisme est identique pour un fait vrai ou caché.
- Tirages dans `{seed}:demeanor`. La didascalie et l'avatar n'ont rien à changer : ils lisent les signes.

Tests : contrat de prestation inchangé (`performance.json`), absence de signature du mensonge (paires contrôlées), rapport
de fidélité.

### Lot 5 : temps d'attente (PR 6)

- **A12.** La session reçoit déjà la chronologie de l'apprenant en mode vocal. Un silence de plus de `wait_turn_ms`
  après la réponse produit un tour « suite » sans question, comme un facilitateur.
- En mode texte, l'interface Streamlit gagne un bouton « Attendre ».
- Le journal enregistre le tour d'attente comme un énoncé vide typé `wait`, que le classifieur ne voit pas.

### Reporté

- **A14, plusieurs séances et rétractation.** C'est un gros chantier qui touche le format des journaux et les
  scénarios. À rouvrir si la formation vise les entretiens répétés.
- **Fatigue.** Il n'existe pas de données (confrontation, §4.8).

## Ordre et dépendances

```text
lot 0 socle ──┬── lot 1 réticence (A1, A2, A3, A6)
              ├── lot 2 classifieur (A4, A5, A7, A13, A15) ── lot 3 mensonge (A8, A9)
              ├── lot 4 corps (A10, A11)   [après le lot 1 : la réticence peut monter]
              └── lot 5 attente (A12)
```

- Les lots 1 et 2 sont indépendants. Le lot 3 dépend du lot 2 (champ `promise`), et le lot 4 du lot 1.
- Les PR sont empilées quand elles dépendent l'une de l'autre, avec le reciblage habituel avant chaque fusion.

## Vérification commune à chaque lot

1. `uv run pytest`, dont `test_mvp_logs_replay_identically`.
2. Rapport `experiments/fidelity/` : les mesures du lot atteignent leur cible, et celles des lots précédents ne régressent
   pas.
3. Ablation hybride contre LLM seul (`experiments/ablation/`) relancée aux lots 1 et 2. Le taux de dévoilement prématuré
   reste à 0 %.
4. Pour les lots 2 et 3 : un entretien réel avec le classifieur LLM (`qwen3.8`) et le réalisateur (`gemma4:31b`) sur s01
   et s08, relu à la main.
5. Une vidéo de démonstration recapturée si le corps change (lot 4).

## Décisions ouvertes

- **Valeurs initiales** : proposition chiffrée à chaque PR, marquée `estimated`, avant la relecture par un formateur
  NICHD.
- **Suivi de l'apprenant** : les alertes « je ne sais pas rejeté » et « question répétée » sont-elles des écarts (rouge)
  ou des points à surveiller (orange) ? Proposition : orange, rouge si la répétition est suggestive.
