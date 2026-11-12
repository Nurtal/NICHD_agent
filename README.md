# Simulateur d'audition NICHD

Simulateur d'entraînement au protocole d'audition NICHD : un moteur de comportement
déterministe décide de ce que dit l'enfant simulé, un LLM local ne fait que le mettre en mots.

- Conception : [docs/design.md](docs/design.md) · Décision d'architecture : [docs/adr/](docs/adr/)
- Vocabulaire : [GLOSSARY.md](GLOSSARY.md)

## Démarrage

```bash
uv sync
uv run pytest
uv run nichd-sim play scenarios/s01_bagarre_parc.yaml --trainer
# voix de l'enfant par LLM local (Ollama, qwen3.8 par défaut)
uv run nichd-sim play scenarios/s01_bagarre_parc.yaml --trainer --realizer llm
# entretien libre : classification automatique + voix LLM
uv run nichd-sim play scenarios/s01_bagarre_parc.yaml --trainer --classifier llm --realizer llm
```

En classification manuelle (par défaut), préfixez chaque énoncé par son type :
`[inv] Dis-moi tout ce qui s'est passé.`, `[dir:d_pousse] Qui a poussé ?` (tapez `/aide`, `/unites`).
Les journaux de session sont écrits dans `sessions/`.
