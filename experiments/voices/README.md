# Criblage des voix de synthèse (TTS)

Comparaison de **Kokoro** (82 M, Apache-2.0) et **Chatterbox multilingue** (Resemble AI, MIT) pour la voix de l'enfant
(ADR 0002, étape 4). Tout tourne en local.

## Installation (une fois)

Chaque moteur a son propre environnement : leurs versions de torch sont incompatibles, et aucun ne touche au venv du
projet (le MVP texte reste léger). Pilote NVIDIA 575 / CUDA 12.9 : prendre torch **cu126** (les roues par défaut
visent CUDA 13).

```bash
E=experiments/voices/.envs
uv venv --python 3.11 $E/kokoro
VIRTUAL_ENV=$E/kokoro uv pip install "kokoro>=0.9.4" "misaki[fr]" soundfile scipy faster-whisper librosa jiwer
VIRTUAL_ENV=$E/kokoro uv pip install --reinstall torch --index-url https://download.pytorch.org/whl/cu126
uv venv --python 3.11 $E/chatterbox
VIRTUAL_ENV=$E/chatterbox uv pip install chatterbox-tts "setuptools<80"   # perth (filigrane) a besoin de pkg_resources
```

Modèles téléchargés au premier lancement dans le cache Hugging Face : `hexgrad/Kokoro-82M` (~330 Mo),
`ResembleAI/chatterbox` (~3 Go). Whisper large-v3 (`Systran/faster-whisper-large-v3`) sert de juge.

## Lancer

```bash
experiments/voices/run.sh
```

1. `make_corpus.py` : les **segments que le moteur envoie vraiment** à la voix (plans d'élocution de sessions
   scriptées, s08 compris), y compris les **fragments** coupés par les pauses (« J'avais », « était là. »).
2. `synth_kokoro.py`, `synth_chatterbox.py` : une variante par voix, au débit 1,0 et 0,75 ; seed fixée par segment.
   - **voix d'enfant** : hausse de la hauteur *et* des formants d'un facteur 1,25 (≈ +3,9 demi-tons). Pour Kokoro,
     la synthèse se fait à vitesse ÷ 1,25 puis on rééchantillonne, ce qui garde la durée. Pour Chatterbox, on utilise
     un `pitch_shift` ;
   - **clone** : Chatterbox clone un extrait de la voix d'enfant Kokoro, entièrement synthétique. Jamais la voix
     d'un enfant réel ;
   - Chatterbox n'a pas de réglage de débit : le débit est appliqué après coup (vocodeur de phase).
3. `evaluate.py` : intelligibilité (WER/CER par Whisper large-v3), F0 médiane, respect du débit, hallucinations,
   latence, mémoire, déterminisme → `results/screening.md`.

Les fichiers audio (`results/audio/`, non versionnés) servent à l'écoute : l'évaluation objective ne dit rien du
naturel ni de l'âge perçu.

## Conversations vocales scriptées

`conversations/*.yaml` : des tours d'interviewer, soit en texte (dit par la voix adulte de Kokoro), soit en
enregistrement WAV (`wav: chemin`, par exemple enregistré sur votre poste puis copié). `after_ms` fixe le début de
l'enregistrement par rapport à la fin de la réponse de l'enfant ; une valeur négative fait parler l'interviewer
par-dessus l'enfant. `tag` donne la classification manuelle (sans LLM).

```bash
uv run nichd-sim converse experiments/voices/conversations/s08_interruptions.yaml -o audio/conv --trainer
# avec le classifieur LLM (les tags sont alors ignorés)
uv run nichd-sim converse … --classifier llm --realizer llm
```

Sorties : `conversation.wav` (toute la conversation sur une seule piste), `conversation.json` (qui parle quand) et
le journal de session.

Limite constatée : Whisper transcrit mal les énoncés très courts de la voix de synthèse (« Et après ? » → « Il
apprêt. »). À vérifier sur de vraies voix.
