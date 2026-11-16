# ADR 0002 — Mensonge, diction et voix : trois extensions du moteur, sans toucher à l'invariant de l'ADR 0001

- **Statut** : accepté
- **Date** : 2026-11-16
- **Prolonge** : [ADR 0001](0001-architecture-hybride-moteur-deterministe.md)
- **État de référence figé** : tag `v0.1-mvp` (branche `release/mvp`), MVP texte de type chatbot

## Contexte

Le MVP fait jouer un enfant qui ne se trompe que **de bonne foi** : confabulation, acquiescement, contamination
par suggestion. Or, en audition réelle, une difficulté centrale est l'enfant qui **cache ou maquille** des faits,
le plus souvent pour protéger un proche, par peur ou par honte. Le protocole NICHD révisé (soutien, rapport)
a été conçu pour ces enfants réticents.

On veut aussi passer à l'oral. Or, à l'oral, *comment* l'enfant répond (silence avant de parler, pauses,
« euh », débit, voix basse) est une information que le texte perd.

Trois risques encadrent la conception :

1. **Rompre l'invariant de l'ADR 0001** : si le LLM inventait les mensonges, ils deviendraient intraçables et
   pourraient faire fuiter des faits du scénario.
2. **Enseigner un faux indice.** La latence de réponse est un indice de mensonge **très faible** :
   DePaulo et al. (2003) ne trouvent pas d'effet fiable, et Sporer & Schwandt (2006) un effet faible (d ≈ 0,2).
   Un enfant hésite surtout parce qu'il cherche un souvenir, qu'il est gêné ou qu'il n'a pas compris. Si seul le
   mensonge faisait hésiter l'enfant simulé, le simulateur apprendrait aux interviewers « il hésite, donc il ment »,
   c'est-à-dire exactement le biais que la formation combat.
3. **Casser la comparabilité.** Ajouter un tirage aléatoire dans le flux du moteur décalerait toutes les décisions
   suivantes : les journaux, les rejeux et l'ablation existants deviendraient incomparables.

## Décision

### 1. Le mensonge est une décision du moteur, sur un contenu écrit par l'auteur

- Le scénario peut déclarer un bloc **`deception`** facultatif :
  - un **motif** (`loyalty`, `fear`, `shame`, `coached`) ;
  - une **force** initiale ;
  - les **faits protégés** (unités vraies que l'enfant cherche à cacher) ;
  - des **contenus mensongers rédigés** : versions de couverture et minimisations. Chacun a ses ancres, comme une
    unité d'information.
- Le moteur tient une variable d'état, la **pression de dissimulation** (`concealment`). Le soutien et le rapport
  la font baisser. La pression (questions suggestives ou à choix sur un fait protégé) la fait monter.
- Les formes de mensonge, toutes décidées par le moteur :
  - **omission** : un fait protégé est retiré d'un récit libre, sans marque dans le texte ;
  - **dénégation** : « non » à une question oui/non ou suggestive vraie ;
  - **ignorance feinte** : « je sais pas » à une question directive ;
  - **version de couverture** : « je suis tombée dans l'escalier » ;
  - **minimisation** : « il m'a juste un peu poussée ».
- Chaque mensonge est **journalisé** (`LieRecord` : fait protégé, forme, contenu, tour), comme une contamination.
  Cela garantit la cohérence d'un tour à l'autre et des métriques exactes.
- Quand la pression de dissimulation tombe sous un seuil, l'enfant peut **revenir sur un mensonge**
  (`retraction`) et dire le fait vrai.
  - *Attention au vocabulaire* : en psychologie légale, la « rétractation » (*recantation*) désigne le fait de
    revenir sur un dévoilement **vrai**. Ici, c'est l'inverse. Le premier phénomène pourra être modélisé plus tard,
    sous un autre nom.
- **Hors périmètre** : les fausses allégations inventées de toutes pièces. Elles sont rares, délicates sur le plan
  éthique et brouilleraient le message pédagogique.
- Le LLM ne voit toujours que le contenu autorisé du tour, mensonger ou vrai. Le **contrôle de fuite** traite les
  ancres des contenus mensongers comme celles des unités vraies.

### 2. La diction (`Delivery`) est une troisième sortie de la décision, à causes multiples

- Chaque décision porte une **diction** :
  - le silence avant la réponse (`onset_ms`) ;
  - les pauses internes ;
  - les « euh » ;
  - le débit ;
  - le volume.
- La diction résulte d'une **somme de charges**, chacune enregistrée avec sa contribution :
  - `retrieval` : récupération en mémoire (fait périphérique, repère temporel, jeune âge) ;
  - `affect` : émotion (fait central de l'événement cible, réticence) ;
  - `deception` : mensonge en cours ;
  - `confusion` : question composée, choix à options multiples, incompréhension.

  Une variabilité individuelle s'y ajoute.
- Le formateur et le retour voient **pourquoi** l'enfant a hésité. On peut ainsi évaluer la **réaction** de
  l'apprenant à une hésitation (patienter, relancer ouvertement) plutôt que sa capacité à « détecter » un mensonge.

### 3. Des flux aléatoires séparés

- La tromperie et la diction tirent dans leurs **propres générateurs**, dérivés de la seed
  (`Random(f"{seed}:deception")`, `Random(f"{seed}:delivery")`).
- Pour un scénario **sans bloc `deception`**, les décisions (acte et unités) restent **identiques** à celles de
  `v0.1-mvp`. Un test le vérifie en rejouant des journaux produits par le MVP.
- Le format de journal passe à 2. Le rejeu d'un journal au format 1 ignore les champs nouveaux.

### 4. La voix est un port, et l'hésitation est inscrite dans l'audio

- Un port **`Speaker`** reçoit le **plan d'élocution** : segments de parole et silences calculés à partir de la
  réponse filtrée et de la diction. Il renvoie un fichier audio.
- **Les silences sont insérés par nous**, en concaténant les segments, et non demandés au modèle de synthèse.
  On obtient un contrôle exact et rejouable, indépendant du moteur TTS.
- **La latence de calcul est ignorée** (phase de R&D, optimisation plus tard). L'hésitation de l'enfant **est** le
  silence en tête du fichier. La réflexion du classifieur est conservée.
- **Première étape : sortie vocale seule**, l'apprenant tape. La transcription de l'apprenant (STT) et les
  métriques de tour de parole (temps d'attente, interruptions) viendront ensuite.
- **Voix d'enfant synthétique**. On ne clone jamais la voix d'un enfant réel.
- Les dépendances vocales lourdes restent **optionnelles** (`uv sync --extra voice`), pour que le MVP texte reste
  léger.

## Conséquences

### Positives

- Les mensonges sont traçables, reproductibles et mesurables : quels faits ont été cachés, par quel type de
  question le mensonge a été provoqué ou levé.
- Argument pédagogique fort : face à un enfant qui protège un proche, une question fermée « tombée juste » peut
  être niée. Seuls le soutien et les invitations font tomber la dissimulation.
- L'hésitation n'est pas un détecteur de mensonge, ce qui est conforme à la littérature.
- Les décisions du MVP sont inchangées, et rejeu et ablation restent comparables.

### Négatives / risques

- **Nouveaux paramètres, tous estimés** (dynamique de la dissimulation, poids de la diction). Ils sont à relire par
  un chercheur ou un formateur, comme ceux de l'ADR 0001.
- **Coût de rédaction des scénarios** : faits protégés, versions de couverture et minimisations, avec leurs ancres.
- **La réalisation LLM peut ajouter ses propres « euh »** (le registre des 4–6 ans en demande). La diction décidée
  par le moteur s'y superpose. C'est acceptable, mais à surveiller lors du criblage vocal.
- **À l'oral, l'attente perçue = calcul + silence simulé.** C'est sans effet sur le signal enregistré, mais gênant
  en démonstration tant que la latence n'est pas optimisée.

## Alternatives écartées

- **Laisser le LLM décider de mentir** (consigne « tu protèges Karim ») : contraire à l'ADR 0001, car intraçable,
  non reproductible et sans métrique.
- **Hésitation causée par le seul mensonge** : enseigne un faux indice (voir Contexte).
- **Faire générer les pauses par le modèle TTS** (balises SSML, prompts d'émotion) : comportement variable selon le
  modèle et non rejouable.
- **Repo ou branche longue séparés** pour la voix et le moteur : le mensonge touche le cœur (moteur, scénario,
  journal), et deux bases divergeraient. On fige plutôt le MVP par un tag et on garde les nouveautés désactivées
  par défaut.
