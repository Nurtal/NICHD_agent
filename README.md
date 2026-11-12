# Simulateur d'audition NICHD

Simulateur d'entraînement au protocole d'audition NICHD : un moteur de comportement
déterministe décide de ce que dit l'enfant simulé, un LLM local ne fait que le mettre en mots.

- Conception : [docs/design.md](docs/design.md) · Décision d'architecture : [docs/adr/](docs/adr/)
- Vocabulaire : [GLOSSARY.md](GLOSSARY.md)

## Démarrage

Prérequis : Python 3.12, [uv](https://docs.astral.sh/uv/), et pour la voix et la classification
automatiques un serveur [Ollama](https://ollama.com) local avec le modèle `qwen3.8`.

```bash
uv sync
uv run pytest
# interface web (entretien, mode formateur, retour)
uv run nichd-sim ui
# même interface sans LLM (voix gabarit, classification manuelle)
NICHD_OFFLINE=1 uv run nichd-sim ui
```

L'interface n'écoute que sur `127.0.0.1`. Depuis un autre poste, passez par un tunnel SSH
(`ssh -L 8501:127.0.0.1:8501 serveur`) plutôt que d'exposer le port (`--host` à vos risques).

### En ligne de commande

```bash
uv run nichd-sim play scenarios/s01_bagarre_parc.yaml --trainer
# voix de l'enfant par LLM local (Ollama, qwen3.8 par défaut)
uv run nichd-sim play scenarios/s01_bagarre_parc.yaml --trainer --realizer llm
# entretien libre : classification automatique + voix LLM
uv run nichd-sim play scenarios/s01_bagarre_parc.yaml --trainer --classifier llm --realizer llm
```

En classification manuelle (par défaut), préfixez chaque énoncé par son type :
`[inv] Dis-moi tout ce qui s'est passé.`, `[dir:d_pousse] Qui a poussé ?` (tapez `/aide`, `/unites`).
Le classifieur raisonne par défaut (réflexion `medium`, le réglage le plus précis mesuré, ~13 s par question) ; `--classifier-think off` pour une démonstration fluide (~3 s). Options utiles : `--summary` (rédiger une synthèse confrontée aux faits), `--no-rephrase`
(retour sans reformulations LLM). Les journaux de session sont écrits dans `sessions/`.

```bash
# rejouer une session à l'identique depuis son journal (sans LLM)
uv run nichd-sim replay sessions/session_<id>.json
# transcription vierge (CSV ;) pour des codeurs humains
uv run nichd-sim export sessions/session_<id>.json -o codage.csv
# évaluer le classifieur sur le jeu de test du skill (kappa de Cohen)
uv run nichd-sim eval-classifier -o docs/evaluations/rapport.md
```

## Organisation

| Chemin | Rôle |
|---|---|
| `scenarios/` | fiches de scénario (YAML), en attente de validation par un formateur — voir [docs/guide-scenarios.md](docs/guide-scenarios.md) et `nichd-sim check-scenario` |
| `src/nichd_sim/session.py` | façade `Session`, unique point d'entrée (CLI, interface, tests) |
| `src/nichd_sim/engine.py` | moteur de comportement déterministe |
| `src/nichd_sim/phases.py` | suivi des phases et écarts au protocole |
| `src/nichd_sim/skill/` | skill NICHD versionné : spécification, exemples, schéma, jeu de test |
| `src/nichd_sim/data/parameters.yaml` | paramètres de comportement sourcés |
| `docs/evaluations/` | rapports d'évaluation du classifieur |
