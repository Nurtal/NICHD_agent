#!/usr/bin/env bash
# TTS screening: Kokoro vs Chatterbox (see README.md). Each engine has its own venv.
set -euo pipefail
cd "$(dirname "$0")/../.."
E=experiments/voices/.envs
uv run python experiments/voices/make_corpus.py
$E/kokoro/bin/python experiments/voices/synth_kokoro.py
$E/chatterbox/bin/python experiments/voices/synth_chatterbox.py
SP=$(ls -d $E/kokoro/lib/python3.*/site-packages)
export LD_LIBRARY_PATH="$(ls -d "$PWD/$SP"/nvidia/*/lib | tr '\n' ':')${LD_LIBRARY_PATH:-}"
$E/kokoro/bin/python experiments/voices/evaluate.py
