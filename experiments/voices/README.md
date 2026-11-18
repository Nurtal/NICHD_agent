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

Voix de l'enfant par défaut depuis la v2 : **Qwen3-TTS** (Apache-2.0), avec une voix d'enfant synthétique
choisie dans une banque de 6 voix (fille ou garçon, par tranche d'âge du moteur), stockée dans
`src/nichd_sim/data/voices/` :

```bash
uv venv --python 3.11 $E/qwen
VIRTUAL_ENV=$E/qwen uv pip install "qwen-tts==0.1.1" soundfile librosa
VIRTUAL_ENV=$E/qwen uv pip install --reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu126
```

Le modèle `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (~4 Go) est téléchargé au premier lancement. Il occupe environ 5 Go
de mémoire graphique en float16. Sur une TITAN RTX, une réponse courte prend 2 à 5 s et une longue
(une dizaine de secondes de parole) environ 15 s. La variable `NICHD_QWEN_PYTHON` remplace le chemin de cet environnement. Sans
cet environnement, on retombe sur Kokoro, puis sur `tone` ; le mode texte n'a besoin d'aucun des deux.

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

## Criblage v2 : clonage sur références ouvertes, nouveaux modèles (`v2/`)

Rapport : [`docs/evaluations/voix-v2.md`](../../docs/evaluations/voix-v2.md). Un environnement par moteur sous
`.envs/<moteur>` (versions de torch incompatibles entre elles). Pilote 575 : torch cu126 ou cu129, jamais cu130.
Les cartes Turing n'ont pas de bf16 : float16 ou float32.

1. `v2/fetch_references.py` puis `v2/transcribe_references.py` : clips de référence de 10–20 s, 24 kHz, dans
   `v2/references/` (non versionné), décrits dans `references.json` (source, licence, raison du choix) :
   - lectrices adultes de **MLS French** (CC BY 4.0) ;
   - actrices adultes de **CaFE** (CC BY-NC-SA 4.0), neutre, peur et tristesse ;
   - voix d'enfant **entièrement synthétiques** : conçues par Qwen3-TTS VoiceDesign (fille de 8 ans, garçon de
     6 ans), et l'ancienne voix Kokoro enfant.

   Jamais la voix d'un enfant réel (ADR 0002).
2. `v2/synth_<moteur>.py`, un par moteur et lancé avec le Python de son environnement. Chaque moteur dit
   - les segments du criblage v1 ;
   - 12 réponses entières, synthétisées d'un bloc avec leurs pauses « … » et leurs « euh ».

   Il produit une variante par référence. Moteurs : `synth_qwen.py`, `synth_kyutai.py`,
   `synth_clone_engines.py xtts|chatterbox`, `synth_higgs.py`, `synth_f5.py`, `synth_fish.py`.
3. `v2/evaluate_v2.py` (env kokoro) mesure WER/CER Whisper, hallucinations, F0, pauses rendues et RTF, et écrit
   `v2/results/screening_v2.md`. Un cache par fichier permet de relancer seulement ce qui a changé.
4. Écoute à l'aveugle :
   - `uv run python v2/listening/build_listening.py` prépare les extraits, appariés en volume et renommés au
     hasard ;
   - `python3 v2/listening/serve.py --port 8600` sert la page ; il ne sert jamais `design.json`, la clé des
     extraits ;
   - `v2/listening/analyze.py` dépouille les notes enregistrées dans `ratings/`.

Assemblage : `nichd_sim.voice.render.RenderStyle` ajoute un fond sonore à la place du silence numérique, des fondus
plus longs et un mode « natif » (réponse d'un bloc, chronologie mesurée). Il est facultatif ; le rendu par défaut
est inchangé.
