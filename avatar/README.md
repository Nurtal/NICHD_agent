# Avatar — rejeu d'une session, vue « user » et vue « dev »

Premier « corps » du simulateur ([ADR 0004](../docs/adr/0004-avatar-contrat-de-prestation.md)). Le moteur
décide de tout. L'avatar se contente de **jouer** le contrat de prestation (`performance.json`) : mots,
chronologie de la parole, voix et signes du corps. Il ne contient aucune logique métier.

## Lancer

```bash
# 1. Exporter un journal de session (sessions/*.json) ; --voice rend l'audio, --debug-map la carte de la vue dev
uv run nichd-sim export-avatar sessions/session_XXXX.json -o avatar_sessions/demo --voice --debug-map
# 2. Servir l'avatar et la session (127.0.0.1, passe par le tunnel SSH comme l'UI)
uv run nichd-sim avatar avatar_sessions/demo --port 8600
# 3. Ouvrir http://127.0.0.1:8600/ puis « Lancer le rejeu »
```

Options d'URL :
- `?mode=user` (défaut) ou `?mode=dev` : la vue, aussi réglable avec le bouton **Dev / User** ;
- `?map=1` : vue dev avec la carte, `?map=0` : vue dev sans la carte ;
- `?turn=N` : tour de départ ;
- `?autoplay=0` : pas d'enchaînement automatique ;
- `?at=MS` : figer la réponse à cet instant (captures) ;
- `?start=1` : démarrer sans cliquer (l'audio peut alors être bloqué par le navigateur) ;
- `?debrief=1` : ouvrir le bilan (captures).

Sans `--voice`, la chronologie est estimée (environ 65 ms par caractère, silences exacts) et l'avatar reste
muet.

## Vue user : l'entretien

L'enfant est assis dans une salle d'audition adaptée aux mineurs (« salle Mélanie »), construite en three.js sans
fichier externe. Le décor reste sobre pour ne pas distraire. Le corps ne s'exprime que par ses mouvements, ses larmes
et la didascalie : aucune couleur de débogage.

Le panneau de droite vient de `coaching.json`, écrit par `export-avatar` quand le scénario est trouvé :
- **Faits** : faits recueillis sur faits à recueillir. Le compteur monte à la fin de la réponse ;
- **Phase du protocole** : phase en cours, phases passées, phases sautées (hachurées) ;
- **Journal** : chaque phrase de l'interviewer, taguée `conforme`, `à surveiller` ou `écart`, avec ses alertes.

Le tag et l'alerte du tour s'affichent aussi avec la question. Le **bilan** apparaît à la fin du rejeu.

Le suivi ne doit pas servir de détecteur de vérité (voir l'ADR 0004) :
- un fait obtenu par une suggestion tombée juste n'est compté qu'au bilan ;
- dans un scénario avec dissimulation, le compteur affiche `? / N` jusqu'au bilan.

Le barème des niveaux est une proposition, à valider par un formateur NICHD.

## Vue dev : ce que fait le corps

- **Axe du regard** : la flèche rose suit l'orientation réelle de la tête et des yeux. Les pointillés montrent la
  direction de l'interviewer. La légende donne les angles.
- **Surbrillance** : les parties du corps mises en jeu par les signes s'éclairent, à la couleur de la famille.
  La légende indique les parties de chaque signe.
- **Halo au sol** : l'activation, du bleu au rouge.
- **Carte du système** : avec `--debug-map`, la carte (celle de la vue « Graphe du système » de l'UI) suit le tour :
  classification pendant la question, décision au début de la réponse, fin quand la réponse est finie.

La carte est un **canal de débogage, hors contrat** : elle montre les rouages du moteur (règle, mensonge, filtre),
que `performance.json` ne contient jamais. Sans `--debug-map`, le bouton **Carte** est désactivé.

| Famille | Couleur | Mouvement (dans les deux vues) |
|---|---|---|
| Regard (`gaze`) | rose | tête et yeux tournés (fuyant), baissés, ou regard fixe sans mouvement des yeux |
| Agitation (`fidget`) | jaune | jambes, mains, ou une main qui frotte la manche |
| Crispation (`tension`) | rouge | épaules relevées, poings serrés, bouche serrée |
| Respiration (`breathing`) | orange | tronc qui pulse vite, ou immobile |
| Tremblement (`tremor`) | violet | mains ou menton qui vibrent |
| Repli (`withdrawal`) | gris foncé | bras serrés, genoux remontés, buste penché |
| Figement (`freeze`) | gris | plus aucun mouvement, tête qui s'affaisse si l'enfant est absent |
| Pleurs (`tears`) | bleu | larme au coin de l'œil, larmes qui coulent |
| Détente (`ease`) | vert | léger recul, sourire |

Voix :
- la bouche s'ouvre sur les segments parlés du plan d'élocution, y compris les « euh » et les faux départs ;
- elle s'ouvre moins quand l'enfant parle à voix basse ou chuchote ;
- elle vibre quand la voix tremble.

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | page, panneaux des deux vues, three.js épinglé (`0.170.0`, jsDelivr) |
| `figure.js` | scène, caméras des vues, enfant stylisé (pivots et un matériau par partie du corps) |
| `room.js` | salle d'audition (vue user) |
| `cues.js` | signe → mouvement et parties du corps (cibles lissées, animation) |
| `debug.js` | axe du regard, surbrillance, halo (vue dev) |
| `coaching.js` | suivi du protocole et bilan (vue user) |
| `main.js` | chargement des données, vues, horloge (audio ou interne), enchaînement des tours |
| `record_demo.py` | enregistre une vidéo du rejeu avec la voix (`--mode user` ou `dev`, Playwright + ffmpeg) |

## Suite (ADR 0004)

1. Direct par WebSocket.
2. WebXR.
3. Vrai modèle 3D à la place de l'enfant stylisé, avec le même contrat.
