# Présentation du prototype

| Fichier | Contenu |
|---|---|
| `slides.pdf` | 14 slides : principe, architecture hybride, scénario, moteur, contamination, phases, classifieur, démo, retour, traçabilité, utilisation, suite |
| `demo_nichd.mp4` | *Non versionnée (`.gitignore`), présente en local sur la station.* Vidéo de démonstration (3 min 30) : entretien complet avec Léo, 5 ans (scénario s01, graine 1), puis écran de retour |
| `demo-moteur-en-direct-x2.mp4` | *Non versionnée.* Vue « Moteur en direct » (2 min, accélérée ×2) : Emma, 8 ans (s02, réticence abaissée à 0,10 depuis le profil, graine 0), 8 tours. On voit l'état interne, la trajectoire, les 7 étapes du tour et les faits qui se révèlent. Version à vitesse réelle : `demo-moteur-en-direct.mp4` (4 min 12) |
| `demo-graphe-systeme-x2.mp4` | *Non versionnée.* Vue « Graphe du système » (1 min 45, accélérée ×2), même entretien : la carte du système s'allume en direct pendant chaque tour (classifieur et réalisateur qui pulsent pendant l'appel au LLM, règle choisie, filtre, repli en rouge au tour 6). Version à vitesse réelle : `demo-graphe-systeme.mp4` (3 min 30) |
| `demo-avatar-emma.mp4` | *Non versionnée.* Avatar jalon 1 (1 min 22, avec la voix Kokoro) : rejeu d'un entretien d'Emma (s02, réticence 0,10, graine 0, vrai modèle `qwen3.8`, 9 tours) sur l'enfant en formes simples. Marqueurs de couleur, légende, sous-titres. Enregistrée avec `avatar/record_demo.py` |
| `record_engine_demo.py` | Rejoue et enregistre ces deux démos (Playwright, Chrome sans interface ; `--graph` pour la carte) |
| `slides.html` | Source des slides |
| `build_pdf.py` | Régénère `slides.pdf` à partir de `slides.html` (Chrome sans interface) |
| `img/` | Captures extraites de la vidéo |
| `architecture.pdf` | 7 schémas d'architecture : vue d'ensemble d'un tour, ce que voit chaque LLM, décision du moteur, règles par type de question, phases, mensonge et diction, journal et carte du code |
| `architecture.html` | Source des schémas (SVG en ligne, même format 1280 × 720 que les slides). PDF : même commande que ci-dessous, en remplaçant `slides` par `architecture` dans `build_pdf.py` |

Régénérer le PDF :

```bash
cd docs/presentation
uv run --no-project --with playwright python build_pdf.py
```

Conditions de la vidéo : vrai modèle local (`qwen3.8:latest` via Ollama), classifieur sans réflexion
(`NICHD_CLASSIFIER_THINK=off`) pour garder un rythme fluide, mode formateur activé.
