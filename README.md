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

### Mensonge, diction et voix (R&D, [ADR 0002](docs/adr/0002-mensonge-diction-voix.md))

L'état texte « chatbot » est figé au tag `v0.1-mvp` (branche `release/mvp`). Depuis :

- chaque réponse a une **diction** (silence avant de répondre, pauses, « euh », débit, volume) à causes multiples
  (mémoire, émotion, mensonge, confusion), visible en mode formateur ;
- un scénario peut faire **cacher ou maquiller** des faits par l'enfant (bloc `deception`, exemple
  `scenarios/s08_violences_maison_secret.yaml`) ;
- la réponse peut être rendue en **audio** (optionnel : sans `--voice`, tout reste en texte, et sans l'environnement voix
  le projet et ses tests fonctionnent, les tests audio sont ignorés), l'hésitation étant inscrite dans le fichier (silences exacts) :

```bash
uv run nichd-sim play scenarios/s08_violences_maison_secret.yaml --trainer --voice audio/
uv run nichd-sim render-audio sessions/session_<id>.json -o audio/<id>   # rejouer un journal en audio
```

Voix : `kokoro` (enfant, défaut si installé), `kokoro-adulte`, ou `tone` (bourdonnement sans modèle, pour vérifier le
rythme). Kokoro tourne dans son propre environnement, sans toucher au venv du projet : installation et criblage dans
[experiments/voices/](experiments/voices/README.md). La réponse est synthétisée en un seul énoncé puis coupée aux pauses,
ce qui garde une intonation continue.

L'apprenant peut aussi **parler** : la transcription (Whisper large-v3, même environnement que Kokoro) mesure quand il
prend la parole. S'il coupe l'enfant (pendant son hésitation, une pause ou une phrase), ce que l'enfant n'a pas eu le
temps de dire **n'est pas compté comme dit** : il pourra le redire plus tard. Le retour indique l'attente médiane, les
interruptions et les hésitations respectées. Sans interface micro pour l'instant, on scripte la conversation (texte dit
par la voix adulte, ou enregistrements WAV) :

```bash
uv run nichd-sim converse experiments/voices/conversations/s08_interruptions.yaml -o audio/conv --trainer
uv run nichd-sim transcribe mon_enregistrement.wav
```

## Organisation

| Chemin | Rôle |
|---|---|
| `scenarios/` | fiches de scénario (YAML), en attente de validation par un formateur — voir [docs/guide-scenarios.md](docs/guide-scenarios.md) et `nichd-sim check-scenario` |
| `src/nichd_sim/session.py` | façade `Session`, unique point d'entrée (CLI, interface, tests) |
| `src/nichd_sim/engine.py` | moteur de comportement déterministe (révélation, contamination, mensonge) |
| `src/nichd_sim/delivery.py` | diction : hésitation à causes multiples, plan d'élocution |
| `src/nichd_sim/voice/` | couche voix : port `Speaker`, rendu audio des plans d'élocution |
| `src/nichd_sim/phases.py` | suivi des phases et écarts au protocole |
| `src/nichd_sim/skill/` | skill NICHD versionné : spécification, exemples, schéma, jeu de test |
| `src/nichd_sim/data/parameters.yaml` | paramètres de comportement sourcés |
| `docs/evaluations/` | rapports d'évaluation du classifieur |
