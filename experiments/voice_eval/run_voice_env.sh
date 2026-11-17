#!/usr/bin/env bash
# Run a voice_eval script in the voice venv (numpy, librosa, faster-whisper; see experiments/voices/README.md).
set -euo pipefail
cd "$(dirname "$0")"
E=../voices/.envs/kokoro
SP=$(ls -d $E/lib/python3.*/site-packages)
export LD_LIBRARY_PATH="$(ls -d "$PWD/$SP"/nvidia/*/lib | tr '\n' ':')${LD_LIBRARY_PATH:-}"
exec $E/bin/python "$@"
