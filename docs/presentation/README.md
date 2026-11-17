# Présentation du prototype

| Fichier | Contenu |
|---|---|
| `slides.pdf` | 14 slides : principe, architecture hybride, scénario, moteur, contamination, phases, classifieur, démo, retour, traçabilité, utilisation, suite |
| `demo_nichd.mp4` | *Non versionnée (`.gitignore`), présente en local sur la station.* Vidéo de démonstration (3 min 30) : entretien complet avec Léo, 5 ans (scénario s01, graine 1), puis écran de retour |
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
