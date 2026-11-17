# Avatar (jalon 1) — rejeu d'une session sur un enfant en formes simples

Premier « corps » du simulateur ([ADR 0004](../docs/adr/0004-avatar-contrat-de-prestation.md)). Le moteur
décide de tout. L'avatar se contente de **jouer** le contrat de prestation (`performance.json`) : mots,
chronologie de la parole, voix et signes du corps. Il ne contient aucune logique métier.

## Lancer

```bash
# 1. Exporter un journal de session (sessions/*.json) ; --voice rend l'audio (Kokoro si installé, sinon voix « tone »)
uv run nichd-sim export-avatar sessions/session_XXXX.json -o avatar_sessions/demo --voice
# 2. Servir l'avatar et la session (127.0.0.1, passe par le tunnel SSH comme l'UI)
uv run nichd-sim avatar avatar_sessions/demo --port 8600
# 3. Ouvrir http://127.0.0.1:8600/ puis « Lancer le rejeu »
```

Options d'URL :
- `?turn=N` : tour de départ ;
- `?autoplay=0` : pas d'enchaînement automatique ;
- `?at=MS` : figer la réponse à cet instant (captures) ;
- `?start=1` : démarrer sans cliquer (l'audio peut alors être bloqué par le navigateur) ;
- `?map=1` : afficher la carte du système en arrière-plan (voir plus bas).

## Carte du système en arrière-plan (débogage)

`--debug-map` exporte aussi, dans `debug/`, la carte du système (celle de la vue « Graphe du système » de
l'UI) pour chaque tour, en 3 étapes : classification, décision, fin du tour.

Le bouton **Carte**, ou `?map=1` dans l'URL, l'affiche derrière l'enfant, qui se décale alors vers la droite.
La carte suit le tour :
- étape « classification » pendant la question ;
- étape « décision » au début de la réponse ;
- étape « fin » quand la réponse est finie.

C'est un **canal de débogage, hors contrat**. La carte montre les rouages du moteur (règle, mensonge,
filtre), que `performance.json` ne contient jamais. Sans `--debug-map`, le bouton est désactivé.

Sans `--voice`, la chronologie est estimée (environ 65 ms par caractère, silences exacts) et l'avatar reste
muet.

## Marqueurs provisoires

Les comportements fins sont rendus par des **couleurs et des mouvements simples**. La légende, à droite,
affiche toujours les signes actifs avec leur couleur.

| Famille | Couleur | Rendu |
|---|---|---|
| Activation | halo au sol, du bleu au rouge | respiration plus ample et plus rapide |
| Regard (`gaze`) | rose | tête et yeux tournés (fuyant), baissés, ou pupilles grises (fixe, dans le vide). Un rayon rose montre où regarde l'enfant dès que son regard quitte l'interviewer |
| Agitation (`fidget`) | jaune | jambes, mains, ou une main qui frotte la manche |
| Crispation (`tension`) | rouge | épaules relevées, poings serrés, bouche serrée |
| Respiration (`breathing`) | orange (rapide), vert d'eau (retenue) | tronc qui pulse vite, ou immobile |
| Tremblement (`tremor`) | violet | mains ou menton qui vibrent |
| Repli (`withdrawal`) | gris foncé | bras serrés, genoux remontés, buste penché |
| Figement (`freeze`) | gris | plus aucun mouvement, visage grisé |
| Pleurs (`tears`) | bleu | yeux bleus, larmes qui coulent |
| Détente (`ease`) | vert | buste vert, léger recul, sourire |

Voix :
- la bouche s'ouvre sur les segments parlés du plan d'élocution, y compris les « euh » et les faux départs ;
- elle s'ouvre moins quand l'enfant parle à voix basse ou chuchote ;
- elle vibre quand la voix tremble.

## Fichiers

| Fichier | Rôle |
|---|---|
| `index.html` | page, HUD (question, didascalie, sous-titre, légende), three.js épinglé (`0.170.0`, jsDelivr) |
| `figure.js` | scène, chaise, enfant en formes simples (pivots et matériaux exposés) |
| `cues.js` | signe → marqueur (cibles lissées, animation) |
| `main.js` | chargement du contrat, horloge (audio ou interne), enchaînement des tours |
| `record_demo.py` | enregistre une vidéo du rejeu avec la voix (Playwright + ffmpeg) |

## Suite (ADR 0004)

1. Direct par WebSocket.
2. WebXR.
3. Vrai modèle 3D à la place des marqueurs, avec le même contrat.
