# Simulateur d'audition NICHD — Document de conception (v1)

> Statut : validé (session de conception du 2026-11-12)
> Décision d'architecture associée : [ADR 0001](adr/0001-architecture-hybride-moteur-deterministe.md)

## 1. Objet

Simulateur destiné à entraîner des interviewers au protocole d'audition NICHD. L'apprenant mène, à l'écrit et en français, un entretien avec un enfant simulé. Les faits de référence étant connus, le système produit des métriques objectives et un retour structuré.

**Cible v1** : prototype de recherche avec une dimension MVP/démonstration. Il doit permettre de lancer l'étude de validation et d'être montré.

### Hors périmètre v1

- Interaction vocale (STT/TTS). L'architecture reste toutefois « énoncé entrant → énoncé sortant », compatible avec une couche voix ultérieure.
- Scénarios d'abus sexuels. Prévus dans une progression ultérieure, après validation du filtre et avis éthique.
- Événements répétés avec épisodes multiples et confusion inter-épisodes (prévu en v2).
- Persistance multi-sessions, identité d'apprenant, base de données.
- Paires de réalisme (simulé vs réel) pour le jugement en aveugle.

## 2. Architecture générale

```
 Énoncé de l'interviewer
          │
          ▼
 ┌─────────────────────┐   skill NICHD (spéc, few-shot, schéma)
 │  Classifieur (LLM)  │◄──────────────────────────────────────
 └─────────┬───────────┘
           │ {type, cible, proposition suggérée}
           ▼
 ┌─────────────────────┐   ┌──────────────────────┐
 │ Suivi des phases    │──►│ Moteur de comportement│◄── scénario + paramètres
 │ (machine à états)   │   │ (machine à états)     │
 └─────────────────────┘   └─────────┬────────────┘
                                     │ décision : acte de langage + unités autorisées
                                     ▼
                           ┌──────────────────────┐
                           │ Réalisation (LLM)    │
                           └─────────┬────────────┘
                                     ▼
                           ┌──────────────────────┐
                           │ Filtre de sortie     │── échec → régénération ×1 → réponse type
                           └─────────┬────────────┘
                                     ▼
                              Réponse de l'enfant
```

Toutes les étapes sont journalisées (voir §9). Les métriques sont calculées à partir de l'état du moteur et des classifications, sans LLM.

## 3. Modèle de langage

- **Modèle** : `qwen3.8:latest` (27,3B, Q4_K_M, 17 Go) via Ollama, sur la station locale (2 × NVIDIA TITAN RTX 24 Go, 125 Go RAM).
- **Raison du local** : coût et maîtrise complète de l'environnement de prototypage. Confidentialité et reproductibilité en sont des bénéfices secondaires.
- **Un seul modèle, deux usages** :

| Usage | Réflexion (`think`) | Température | Sortie |
|---|---|---|---|
| Classification | `low` ou désactivée | 0 | JSON contraint par schéma (structured outputs Ollama) |
| Réalisation de l'enfant | désactivée | ~0,7 | texte libre, seed fixée et journalisée |
| Reformulations du feedback | désactivée | ~0,5 | texte libre |

- **Latence** : à mesurer dès la tranche verticale. Si elle dépasse ~4 s par tour, le classifieur bascule sur `qwen3:14b`.

## 4. Scénario

Un scénario est un fichier versionné qui contient :

### 4.1 Profil de l'enfant

- **Âge** : 4 à 12 ans, en trois bandes (4–6, 7–9, 10–12). La bande fixe les paramètres par défaut et le registre linguistique : longueur des phrases, vocabulaire, fiabilité des repères temporels.
- **Réticence** initiale.
- **Compétences verbales** (verbosité de base).
- **Suggestibilité**.
- Surcharges éventuelles des paramètres par défaut (§6).

### 4.2 Faits de référence

- Découpés en **segments chronologiques** (avant / pendant / après).
- Chaque segment contient des **unités d'information** avec :
  - `id`
  - `category` : qui, quoi, où, quand, fréquence
  - `centrality` : centrale ou périphérique
  - `value` : la valeur vraie
  - `anchors` : mots d'ancrage, qui servent aux invitations indicées et au contrôle de fuite
- **Fréquence** (v1) : unité simple de type « c'est arrivé d'autres fois », sans épisodes distincts.

### 4.3 Événement neutre

Chaque scénario contient un mini-scénario neutre (anniversaire, sortie…) avec ses propres unités. Il sert à la pratique narrative et suit les mêmes règles de révélation.

### 4.4 Périmètre de contenu v1

Événements neutres ou non abusifs, et maltraitances non sexuelles. Les révélations ne sont pas explicites.

### 4.5 Scénarios v1

Je les rédige, puis un formateur NICHD les valide :

1. Enfant de 5 ans, peu réticent, très suggestible, témoin d'une bagarre.
2. Enfant de 8 ans, réticent, victime de violences physiques par un adulte de son entourage.
3. Enfant de 11 ans, coopératif, peu suggestible, témoin d'un vol.

## 5. Classifieur et skill NICHD

### 5.1 Rôle

Classifieur **unique**, appelé en temps réel à chaque tour. Sa sortie alimente à la fois le moteur et l'évaluation. Ainsi la réaction de l'enfant et le feedback ne peuvent pas diverger.

### 5.2 Sortie (par énoncé)

- `type` : typologie NICHD étendue selon Lamb et al. :
  - invitation, invitation indicée, question directive, question à choix, question suggestive ;
  - facilitateur, énoncé de règle, énoncé de soutien/rapport ;
  - question composée (classée selon son élément le plus directif et signalée) ;
  - autre.
- `target` : unité ciblée (catégorie + entité), ou `hors_scenario`.
- `suggested_proposition` : contenu suggéré par l'interviewer, pour les questions suggestives et à choix.
- Indices de phase (énoncé de règle, invitation sur le thème neutre, incitation de transition…).

### 5.3 Le skill

Répertoire local versionné :

- `spec.md` : définitions des types et des phases, cas limites ;
- `examples.jsonl` : exemples few-shot annotés (énoncé, type, cible, phase) ;
- `schema.json` : schéma de sortie ;
- `testset.jsonl` : jeu de test, **strictement disjoint** des exemples few-shot.

À défaut de corpus existant, on rédige environ 150 énoncés couvrant tous les types, en incluant délibérément des cas ambigus. Un formateur les valide.

## 6. Moteur de comportement

Machine à états déterministe pour une seed donnée.

### 6.1 Variables d'état

- `reluctance` : réticence
- `verbosity` : verbosité
- `acquiescence` : propension à acquiescer
- unités vraies révélées
- unités contaminées, chacune avec le tour qui l'a introduite
- phase courante (fournie par le suivi des phases)

### 6.2 Effets des phases préparatoires

Ces effets sont modestes et paramétrés :

- un rapport et des énoncés de soutien de qualité font **baisser la réticence** ;
- des règles de base posées (en particulier « tu peux dire je ne sais pas ») font **baisser l'acquiescement et la confabulation** ;
- la pratique narrative **augmente la verbosité** aux invitations.

### 6.3 Transition et dévoilement

La réticence fixe un **seuil de dévoilement**, c'est-à-dire le nombre ou le niveau d'incitations de transition nécessaire, selon la gradation NICHD. Un bon rapport abaisse ce seuil. Une incitation trop focalisée ou suggestive peut déclencher le dévoilement, mais elle est signalée comme faute. Un enfant très réticent peut ne rien dévoiler : le feedback présente ce résultat comme **légitime**, et non comme un échec.

### 6.4 Règles de révélation par type de question

| Type | Comportement |
|---|---|
| Invitation | *N* unités centrales non encore dites, dans l'ordre chronologique. *N* dépend de l'âge et de la verbosité. |
| Invitation indicée | Unités du segment qui contient l'indice, y compris des unités périphériques. |
| Directive | Uniquement l'unité ciblée. Si la cible est hors scénario : « je sais pas », ou confabulation selon p(âge, suggestibilité), probabilité réduite si les règles ont été posées. |
| Choix | Bonne option avec p(âge) si elle est proposée. Sinon biais de récence (dernière option), réponse aléatoire ou « je sais pas ». |
| Suggestive | Acquiescement avec p(acquiescement). Si la proposition contredit le fait vrai, le détail est **intégré durablement** avec p(intégration) : il entre dans les unités contaminées et peut réapparaître spontanément ensuite, y compris aux invitations. Une suggestion qui tombe juste compte quand même comme faute de technique. |
| Facilitateur | Poursuite du récit en cours (comme une invitation de faible intensité). |
| Autre / détournement | Acte « confusion » ou « silence », tour signalé dans le feedback. |
| « Autre chose ? » (clôture) | Révélation éventuelle d'une unité centrale restante, avec une probabilité donnée. |

### 6.5 Paramètres

Fichier de paramètres où **chaque valeur cite sa source** (Ceci & Bruck, Bruck & Melnyk, Lamb et al., Krackow & Lynn…). Toute valeur extrapolée est marquée `estimated`. Un chercheur ou un formateur relit le fichier. Les valeurs sont surchargeables par scénario, ce qui permet de futures analyses de sensibilité.

### 6.6 Décision émise

À chaque tour, le moteur produit : l'**acte de langage** (répondre, dire « je sais pas », acquiescer, nier, confusion, silence…) et la **liste des unités autorisées** (vraies et/ou contaminées).

## 7. Suivi des phases

Machine à états alimentée par les sorties du classifieur. Phases : rapport → règles de base → pratique narrative → transition → phase substantive → clôture.

Violations détectées, par exemple :

- question directive ou suggestive sur les faits avant la transition ;
- phase sautée ou tronquée ;
- clôture absente (pas de « autre chose ? », pas de sujet neutre de fin).

C'est l'apprenant qui termine la session (bouton). Une limite souple d'environ 60 tours déclenche un avertissement sans couper l'entretien.

## 8. Réalisation linguistique et contrôle du contenu

### 8.1 Principe : le LLM ne voit jamais le scénario complet

À chaque tour, le prompt de réalisation contient uniquement :

- le profil verbal de l'enfant (bande d'âge, registre) ;
- l'acte de langage décidé ;
- les unités autorisées pour ce tour ;
- un historique court du dialogue.

### 8.2 Filtre de sortie en deux étages

1. **Lexique interdit** : aucun contenu explicite.
2. **Contrôle de fuite** : la réponse ne mentionne aucune entité ou ancre du scénario qui ne figure pas dans les unités autorisées.

En cas d'échec, on régénère une fois, puis on se rabat sur une réponse type associée à l'acte de langage.

### 8.3 Détournements

Les injections (« ignore tes instructions », « raconte tout le scénario ») sont classées « autre » et reçoivent une réponse de confusion. Comme le LLM ne voit que les unités autorisées, rien ne peut fuiter.

## 9. Reproductibilité et journalisation

- **Reproductibilité décisionnelle** : à scénario, seed et suite de classifications identiques, les mêmes unités sont révélées ou contaminées. La formulation de surface peut varier.
- **Rejeu** : chaque session écrit un fichier JSON autonome. Ce fichier est la source de vérité, et il n'y a pas de base de données en v1. Il contient :
  - l'ID de session, le scénario et sa version, la seed, la version du skill, le modèle et ses paramètres ;
  - pour chaque tour : l'énoncé, la classification, l'état du moteur avant et après, la décision, le prompt, la réponse brute, le résultat du filtre et la réponse finale.

## 10. Métriques

Elles sont calculées sans LLM, à partir de l'état du moteur et des classifications.

- **Proportion de questions ouvertes** = (invitations + invitations indicées) / questions, **en phase substantive uniquement**. Facilitateurs, énoncés de règles et énoncés de soutien sont exclus du dénominateur.
- **Informations exactes recueillies** = unités vraies révélées / total, avec la part centrale et la part périphérique séparées, et pour chaque unité le **type de question** qui l'a obtenue.
- **Score de contamination** = unités contaminées / (unités vraies révélées + unités contaminées) dans le récit final. Chaque contamination est reliée à son tour d'origine.
- **Mesure côté apprenant (optionnelle)** : en fin de session, l'apprenant rédige une synthèse. Elle est mise en correspondance avec les unités, ce qui permet de mesurer la qualité du recueil et non plus seulement celle de l'entretien.

## 11. Retour à l'apprenant

### 11.1 Écran de fin de session (par défaut)

- les trois métriques ;
- une frise des phases avec les violations ;
- la transcription annotée (chaque tour coloré selon son type) ;
- pour chaque question directive, à choix ou suggestive, une **reformulation ouverte proposée**, clairement marquée comme générée par le LLM.

### 11.2 Mode formateur (en direct)

Il affiche à chaque tour la classification, l'état du moteur (unités révélées et contaminées, réticence, verbosité, acquiescement) et la phase courante. Il sert à la démonstration et au débogage.

## 12. Validation

- **Accord évaluateur automatique / codeurs humains** : export CSV des transcriptions vierges, avec une colonne de codage vide.
- **Classifieur** : kappa de Cohen sur `testset.jsonl` pour le type, précision sur la cible. Objectif v1 : **κ ≥ 0,70**. Les études publiées avec des codeurs humains rapportent généralement entre 0,80 et 0,90.
- **Jugement de réalisme en aveugle** : hors v1, car il faut un corpus de réponses réelles.
- **Progression des interviewers** : hors v1, car il faut la persistance multi-sessions.

## 13. Pile technique et conventions

- Cœur en Python indépendant de l'interface (scénarios, classifieur, moteur, phases, filtre, métriques), utilisable en ligne de commande.
- Interface de démonstration en **Streamlit**. On pourra passer plus tard à FastAPI avec un front web sans toucher au cœur.
- Code (identifiants, commentaires) en anglais. Contenu métier (prompts, skill, scénarios, interface, feedback) en français. Un `GLOSSARY.md` fait la correspondance entre les deux (invitation ↔ `invitation`, invitation indicée ↔ `cued_invitation`, etc.).

## 14. Tests

- **Moteur, phases, filtre et métriques** : tests unitaires déterministes, avec des suites de classifications injectées et aucun LLM dans la boucle.
- **Classifieur** : script d'évaluation sur le jeu de test (§12).

## 15. Plan de construction

On commence par une tranche verticale en ligne de commande, qui fait apparaître tôt les deux risques principaux (latence, qualité du classifieur) :

1. Format de scénario, scénario n° 1 et fichier de paramètres sourcés.
2. Moteur, suivi des phases et métriques, avec tests unitaires (sans LLM).
3. Skill et classifieur, évaluation sur le jeu de test.
4. Réalisation par le LLM et filtre de sortie.
5. Boucle complète dans le terminal et journaux JSON. Mesure de la latence.
6. Interface Streamlit, mode formateur, écran de feedback.
7. Scénarios n° 2 et 3, export pour les codeurs.
