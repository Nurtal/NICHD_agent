"""Chatterbox multilingual worker (run with experiments/voices/.envs/chatterbox/bin/python).

Variants: built-in voice, child version (pitch shift, duration kept), and a voice cloned from the
*synthetic* Kokoro child clip (never a real child's voice). Chatterbox has no speed parameter:
rate is applied afterwards by time-stretching (phase vocoder). Outputs carry Resemble's Perth
watermark (synthetic speech is marked)."""

from __future__ import annotations

import json
import sys
import time
import zlib
from pathlib import Path

import torch
import torchaudio
import torchaudio.functional as AF
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

HERE = Path(__file__).parent
RES = HERE / "results"
CHILD_SEMITONES = 3.9  # same shift as Kokoro's ×1.25
SPEED_ITEMS = 15


def time_stretch(wav: torch.Tensor, sr: int, rate: float) -> torch.Tensor:
    """Change duration by 1/rate, pitch unchanged (phase vocoder)."""
    if rate == 1.0:
        return wav
    n_fft, hop = 1024, 256
    window = torch.hann_window(n_fft, device=wav.device)
    spec = torch.stft(wav, n_fft, hop, window=window, return_complex=True)
    phase_advance = torch.linspace(0, torch.pi * hop, spec.shape[-2], device=wav.device)[..., None]
    stretched = AF.phase_vocoder(spec, rate, phase_advance)
    return torch.istft(stretched, n_fft, hop, window=window)


def synth(model, text, *, rate=1.0, semitones=0.0, prompt=None, seed=0):
    torch.manual_seed(seed)
    wav = model.generate(text, language_id="fr", audio_prompt_path=prompt)
    if semitones:
        wav = AF.pitch_shift(wav, model.sr, semitones)
    return time_stretch(wav.squeeze(0), model.sr, rate).unsqueeze(0)


def run(model, corpus, variant, rate=1.0, items=None, **kw):
    out = RES / "audio" / (variant if rate == 1.0 else f"{variant}@{rate}")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in corpus[:items] if items else corpus:
        seed = zlib.crc32(item["id"].encode())
        torch.cuda.synchronize()
        t = time.perf_counter()
        wav = synth(model, item["text"], rate=rate, seed=seed, **kw)
        torch.cuda.synchronize()
        dt = time.perf_counter() - t
        torchaudio.save(str(out / f"{item['id']}.wav"), wav.cpu(), model.sr)
        rows.append({"variant": variant, "rate": rate, "id": item["id"], "synth_s": round(dt, 3),
                     "dur_s": round(wav.shape[-1] / model.sr, 3)})
        print(variant, rate, item["id"], round(dt, 2), file=sys.stderr)
    return rows


def main() -> None:
    corpus = json.loads((RES / "corpus.json").read_text(encoding="utf-8"))
    ref = str(RES / "audio" / "ref_kokoro_child.wav")
    t = time.perf_counter()
    model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
    load_s = time.perf_counter() - t
    synth(model, "Bonjour.")  # warm-up
    torch.cuda.reset_peak_memory_stats()
    rows = []
    for variant, kw in (
        ("chatterbox-default", {}),
        ("chatterbox-default-child", {"semitones": CHILD_SEMITONES}),
        ("chatterbox-clone-kchild", {"prompt": ref}),
    ):
        rows += run(model, corpus, variant, **kw)
        rows += run(model, corpus, variant, rate=0.75, items=SPEED_ITEMS, **kw)
    a = synth(model, corpus[2]["text"], seed=1)
    b = synth(model, corpus[2]["text"], seed=1)
    meta = {"engine": "chatterbox", "load_s": round(load_s, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "deterministic": bool(a.shape == b.shape and torch.allclose(a, b)), "sample_rate": model.sr}
    (RES / "synth_chatterbox.jsonl").write_text("\n".join(json.dumps(r) for r in [meta, *rows]) + "\n")
    print(json.dumps(meta), len(rows), "segments", file=sys.stderr)


if __name__ == "__main__":
    main()
