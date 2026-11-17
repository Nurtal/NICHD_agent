# ADR 0003 — Activation émotionnelle et comportement non verbal : le moteur décide, la didascalie n'est qu'un rendu

- **Statut** : accepté
- **Date** : 2026-11-17
- **Prolonge** : [ADR 0001](0001-architecture-hybride-moteur-deterministe.md), [ADR 0002](0002-mensonge-diction-voix.md)

## Contexte

Le moteur de comportement décide déjà, à chaque tour, **ce que** dit l'enfant (acte de langage, unités
autorisées, mensonges) et **comment** il le dit (diction : silence initial, pauses, « euh », débit, volume).
Deux choses manquent.

1. **Un état émotionnel qui dure.** Les charges d'hésitation sont recalculées à chaque tour, sans mémoire. Or un
   enfant bouleversé au tour 12 ne redevient pas calme au tour 13 : une jambe qui s'agite ou une respiration
   rapide persistent.
2. **Le corps.** En audition réelle, l'interviewer voit l'enfant : regard, agitation, crispation, repli, pleurs.
   Un interviewer formé doit percevoir la détresse et y répondre (soutien, pause, retour au rapport), sans
   changer de technique de questionnement.

Pour l'instant, le comportement non verbal est seulement **décrit**, par une didascalie qui précède la réponse.
Sa matérialisation (avatar, voix) viendra plus tard.

Trois risques encadrent la conception. Ce sont ceux de l'ADR 0002, appliqués au corps.

1. **Enseigner un faux indice.** Aucun signe non verbal n'est un indice fiable du mensonge. Dans la méta-analyse
   de DePaulo et al. (2003), le regard fuyant et l'agitation ne sont pas liés au mensonge. Les observateurs
   détectent le mensonge à peine mieux que le hasard (Bond & DePaulo, 2006 : environ 54 %). Si le simulateur
   faisait détourner le regard à l'enfant qui ment, il enseignerait exactement le stéréotype que la formation
   combat.
2. **Laisser le LLM décider.** Un LLM qui écrit librement « *il détourne les yeux* » reproduit ces stéréotypes. Ce
   qu'il écrit n'est ni traçable, ni rejouable, ni mesurable (contraire à l'ADR 0001).
3. **Casser la comparabilité.** Ajouter des tirages dans les flux existants décalerait les décisions et rendrait
   les journaux, les rejeux et l'ablation incomparables.

Un quatrième risque est propre au corps : **assimiler le calme à l'absence d'événement.** Certains enfants
s'agitent, d'autres se figent (visage neutre, voix plate, regard dans le vide). Un simulateur où seule
l'agitation signale la détresse apprendrait qu'un enfant calme n'a rien vécu.

## Décision

### 1. Une variable d'état persistante : l'activation (`arousal`)

- `arousal` (0–1) mesure l'activation émotionnelle de l'enfant. Elle a de l'**inertie** d'un tour à l'autre.
- **Point de départ** : dérivé de la réticence et de la bande d'âge. Aucun nouveau trait de fiche.
- **Elle monte** quand :
  - l'enfant parle de l'événement cible, davantage pour ses faits centraux ;
  - l'interviewer pose des questions suggestives ou à choix ;
  - il y a une violation de phase (aborder l'événement avant le rapport, par exemple) ;
  - l'enfant ment (cause **faible**).
- **Elle baisse** avec le soutien, le rapport et la pratique narrative, et revient lentement vers sa base à
  chaque tour.
- Tous les paramètres sont dans `parameters.yaml`, avec leur source ou la mention `estimated`.
- **L'activation est observable seulement.** Elle pilote la diction et le corps, mais **pas** les actes de
  langage ni les unités révélées. Les décisions restent celles d'aujourd'hui. Coupler l'activation aux décisions
  (plus de réticence, moins de verbosité sous forte activation) est une étape ultérieure, avec sa propre
  évaluation.
- La fatigue (décrochage attentionnel, sessions longues, jeunes enfants) est reportée.

### 2. La diction s'enrichit, à causes multiples

`Delivery` reste l'unique description de la prosodie. Elle gagne :

- un **débit accéléré** (`rate` > 1) : forte activation chez un enfant qui n'est pas figé ;
- des **faux départs** (`false_starts`) : répétition du début de phrase, bafouillement. Ils viennent de l'émotion,
  de la confusion et, faiblement, du mensonge ;
- une **voix tremblante** (`tremor`) : émotion seulement.

La charge `affect` de la diction est alimentée par l'activation.

### 3. Le comportement non verbal (`Demeanor`) est une quatrième sortie de la décision

- Chaque décision porte un **comportement non verbal** : une liste de **signes** tirés d'un **catalogue fermé**,
  chacun avec une **intensité** (`slight`, `clear`, `strong`).

  | Famille | Signes |
  |---|---|
  | Regard | soutenu, fixe dans le vide, fuyant, baissé |
  | Agitation | jambes, mains, tripote un vêtement ou ses cheveux |
  | Crispation | épaules, poings, mâchoire |
  | Respiration | rapide, retenue |
  | Tremblement | mains, menton |
  | Repli | recroquevillé, bras serrés |
  | Figement | immobile, absent |
  | Pleurs | yeux humides, larmes (seulement à forte activation) |
  | Détente | détendu, sourire (rapport, sujets neutres) |

- Le catalogue contient des signes **neutres et positifs**. Sinon, tout geste signalerait un problème, et
  l'indice deviendrait trop facile à lire.
- **Pas de signature non verbale du mensonge.** Le corps suit l'activation, la timidité et l'effort de mémoire. Un
  mensonge porte la même charge émotionnelle que la vérité qu'il cache (règle de l'ADR 0002). Le regard fuyant
  ou baissé vient de l'émotion, de la timidité ou de la recherche en mémoire, jamais du mensonge seul.
- **Style d'expression individuel** : le trait de profil facultatif `expression_style` vaut `agitated` (agité),
  `frozen` (figé) ou `mixed` (mixte). Sa valeur par défaut dépend de la bande d'âge : les 4–6 ans bougent plus.
  Un enfant figé montre peu de signes visibles, même quand son activation est haute (figement, regard fixe, voix
  plate).
- Le comportement non verbal tire dans son propre générateur, `Random(f"{seed}:demeanor")`. Les nouveaux tirages
  de la diction (faux départs, tremblement) y tirent aussi, pour que le flux `{seed}:delivery` reste aligné.

### 4. La didascalie est un rendu par gabarit, pas une génération

- La **didascalie** (`stage_direction`) est une phrase française calculée à partir du comportement non verbal et de
  la diction, par gabarit déterministe : « *Les yeux baissés, les jambes qui s'agitent ; après un long silence, à
  voix basse :* ».
- **Le LLM ne l'écrit pas, et ne la voit pas.** Le réalisateur reste inchangé. On mesurera d'abord, sur des
  transcriptions, les incohérences entre mots et corps (des larmes avec « c'est rien, ça va »), puis on
  corrigera si besoin.
- **L'apprenant** voit la didascalie, sans les causes : c'est à lui de l'interpréter. **Le mode formateur** et le
  journal montrent les signes, l'activation et les causes.

### 5. Comparabilité

- Pour un scénario donné, les **décisions** (acte, unités, mensonges) restent identiques. Les journaux du MVP se
  rejouent à l'identique.
- La **diction** des journaux au format 2 change, puisque la charge `affect` dépend désormais de l'activation.
  Seuls les journaux vocaux récents sont concernés.
- Le format de journal passe à 3. Les formats 1 et 2 se rejouent toujours ; les champs nouveaux sont ignorés.

## Vérification

1. **Rejeu** : les journaux du MVP (`tests/fixtures/mvp_logs`) sont rejoués à l'identique.
2. **Pas de faux indice** : sur s08, pour un même fait protégé, la fréquence de chaque signe est la même, à ε près,
   quand l'enfant ment et quand il dit la vérité. Le critère reprend celui de N2 dans l'évaluation vocale.
3. **Trajectoires** : des apprenants scriptés vérifient que l'activation monte sous des questions suggestives
   répétées et redescend avec le soutien. Un enfant figé à forte activation montre peu d'agitation. Il n'y a
   jamais de pleurs sous le seuil.

## Conséquences

### Positives

- L'apprenant voit l'état de l'enfant et peut y répondre. On pourra évaluer sa **réaction** à la détresse (soutien,
  relance ouverte) plutôt qu'une « lecture » du mensonge.
- Tout est traçable et rejouable : on sait pourquoi l'enfant pleurait au tour 14.
- Le style figé enseigne qu'un enfant calme peut avoir vécu l'événement.

### Négatives / risques

- **Nouveaux paramètres, tous estimés** : dynamique de l'activation, seuils des signes. Ils sont à relire par un
  chercheur ou un formateur NICHD, comme ceux des ADR 0001 et 0002.
- **Le style figé n'est pas encore sourcé.** Il repose sur des observations cliniques (absence d'émotion
  visible chez des enfants maltraités) qu'il faudra documenter.
- **Incohérences mots/corps** tant que le réalisateur ignore le comportement. Elles sont à mesurer.
- **Les gabarits risquent d'être répétitifs** sur une longue session : les variantes doivent suffire.

## Alternatives écartées

- **Didascalie écrite librement par le LLM** : stéréotypes du mensonge, contenu intraçable et non rejouable,
  contraire à l'ADR 0001.
- **Signes réservés au mensonge** : faux indice, voir Contexte.
- **Corps dérivé des seules charges du tour, sans état** : pas d'inertie, un enfant qui passe des larmes au
  sourire en un tour.
- **Module de prosodie distinct de `Delivery`** : deux descriptions concurrentes de la même voix.
- **Trait « anxiété » dans la fiche** : un paramètre de plus à renseigner, sans gain tant que la réticence et
  l'âge suffisent à fixer le point de départ.
