"""Fill ref_text in references/references.json with Whisper large-v3 where it is missing
(run with the kokoro env, which has faster-whisper; see ../run.sh for LD_LIBRARY_PATH)."""

import json
from pathlib import Path

from faster_whisper import WhisperModel

REF = Path(__file__).parent / "references"


def main() -> None:
    index = json.loads((REF / "references.json").read_text(encoding="utf-8"))
    try:
        asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    except Exception:
        asr = WhisperModel("large-v3", device="cpu", compute_type="int8")
    for r in index:
        path = REF / f"{r['id']}.wav"
        if r.get("ref_text") or not path.exists():
            continue
        segments, _ = asr.transcribe(str(path), language="fr", beam_size=5, condition_on_previous_text=False)
        r["ref_text"] = " ".join(s.text.strip() for s in segments)
        r["ref_text_source"] = "whisper-large-v3"
        print(r["id"], "→", r["ref_text"])
    (REF / "references.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
