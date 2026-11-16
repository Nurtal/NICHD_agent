# Comparaison de modèles locaux

Pipeline pour choisir et comparer les modèles qui donnent la voix de l'enfant. Tout tourne en local (Ollama, 2 × TITAN RTX, 48 Go).

1. **Candidats** : `candidates.yaml` (source Ollama ou `hf.co/…`, famille, priorité, options par modèle). Revue : `docs/research/modeles-candidats.md`.
2. **Installation** (télécharge, à lancer sciemment) : `uv run python experiments/models/screen.py --pull --priority 1`
3. **Tri rapide** (~5 min par modèle) : `uv run python experiments/models/screen.py --priority 1`
   - le modèle tient-il entièrement en mémoire GPU ?
   - 7 entretiens hybrides (graine 0) : taux de repli sur gabarit et motifs de rejet du filtre, latence, mots par réponse, sorties de rôle, mots anglais.
   - écrit `results/screening.jsonl` et `results/screening.md`.
4. **Ablation complète** sur les modèles retenus :
   `uv run python experiments/ablation/run.py --config experiments/models/candidates.yaml --models <retenus>`
   puis `uv run python experiments/ablation/analyze.py -o experiments/ablation/results/report.md`.
