"""Reference voices for cloning (voice screening v2). ADRs 0002/0004: never a real child's voice.

    uv run --no-project --with librosa --with soundfile --with numpy python experiments/voices/v2/fetch_references.py

- MLS French (CC BY 4.0, audiobooks read by adults): female readers of the dev/test partitions,
  children's books first; per reader, the clean segment with the highest pitch.
- CaFE (CC BY-NC-SA 4.0, adult actors, Canadian French): female actors, neutral / fear / sadness (low
  intensity), three sentences joined into one ~8 s clip.
Clips: 24 kHz mono, RMS-normalized, in references/ (not versioned); references.json records source,
licence, anonymized speaker and why. ref_text is filled in afterwards by transcribe_references.py.
"""

from __future__ import annotations

import io
import json
import re
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

HERE = Path(__file__).parent
REF = HERE / "references"
CACHE = HERE / ".cache"
SR = 24000
MLS = "https://huggingface.co/datasets/facebook/multilingual_librispeech/resolve/main/data/mls_french"
CAFE = "https://zenodo.org/api/records/1478765/files/CaFE_48k.zip/content"
CHILDREN = re.compile(r"conte|enfant|fée|fable|petit|poucet|alice|pinocchio|chaperon", re.IGNORECASE)
N_MLS = 4
SIBLINGS = [s["rfilename"] for s in json.load(urllib.request.urlopen(
    "https://huggingface.co/api/datasets/facebook/multilingual_librispeech"))["siblings"]]


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print("téléchargement", url)
        urllib.request.urlretrieve(url, path)
    return path


def text(url: str, name: str) -> str:
    return fetch(url, CACHE / name).read_text(encoding="utf-8")


def normalize(y: np.ndarray) -> np.ndarray:
    y = y - np.mean(y)
    rms = np.sqrt(np.mean(y ** 2)) or 1.0
    y = y * (0.08 / rms)
    return np.clip(y, -0.99, 0.99)


def f0_median(y: np.ndarray, sr: int) -> float:
    f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=450, sr=sr, frame_length=1024)
    f0 = f0[voiced & ~np.isnan(f0)]
    return float(np.median(f0)) if len(f0) else 0.0


def snr_proxy(y: np.ndarray) -> float:
    """dB between loud and quiet frames: low means noisy or reverberant."""
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=256)[0] + 1e-9
    return float(20 * np.log10(np.percentile(rms, 95) / np.percentile(rms, 10)))


def mls() -> list[dict]:
    meta = text(f"{MLS}/metainfo.txt", "mls_metainfo.txt").splitlines()[1:]
    rows = [[c.strip() for c in ln.split("|")] for ln in meta if ln.count("|") >= 6]
    female = {}
    for spk, gender, part, _, book, title, _ in rows:
        if gender == "F" and part in ("dev", "test"):
            female.setdefault((part, spk, book), title)
    out = []
    for part in ("dev", "test"):
        trans = dict(ln.split("\t", 1) for ln in text(f"{MLS}/{part}/transcripts.txt", f"mls_{part}_tr.txt").splitlines())
        tars = sorted(Path(f).name[: -len(".tar.gz")] for f in SIBLINGS if f"/mls_french/{part}/audio/" in f)
        candidates = [t for t in tars if (part, t.split("_")[0], t.split("_")[1]) in female]
        candidates.sort(key=lambda t: not CHILDREN.search(female[(part, *t.split("_")[:2])]))
        for tar in candidates[:6]:
            spk, book = tar.split("_")[:2]
            path = fetch(f"{MLS}/{part}/audio/{tar}.tar.gz", CACHE / "mls" / f"{tar}.tar.gz")
            best = None
            with tarfile.open(path) as tf:
                for m in tf.getmembers():
                    if not m.name.endswith((".flac", ".opus", ".wav")):
                        continue
                    seg = Path(m.name).stem
                    y, sr = sf.read(io.BytesIO(tf.extractfile(m).read()))
                    if y.ndim > 1:
                        y = y.mean(axis=1)
                    dur = len(y) / sr
                    if not 9 <= dur <= 20:
                        continue
                    f0, snr = f0_median(y, sr), snr_proxy(y)
                    score = f0 + 2 * snr
                    if best is None or score > best[0]:
                        best = (score, seg, y, sr, f0, snr)
            if best is None:
                continue
            _, seg, y, sr, f0, snr = best
            out.append({"spk": spk, "book_title": female[(part, spk, book)], "seg": seg, "y": y, "sr": sr,
                        "f0": f0, "snr": snr, "text": trans.get(seg, "")})
            print("MLS", spk, female[(part, spk, book)], round(f0), "Hz", round(snr, 1), "dB")
    # one clip per reader, highest pitch first, clean enough
    by_spk = {}
    for c in sorted(out, key=lambda c: -c["f0"]):
        if c["snr"] >= 20 and c["spk"] not in by_spk:
            by_spk[c["spk"]] = c
    return list(by_spk.values())[:N_MLS]


def cafe() -> list[dict]:
    path = fetch(CAFE, CACHE / "CaFE_48k.zip")
    out = []
    with zipfile.ZipFile(path) as z:
        wavs = [n for n in z.namelist() if n.lower().endswith(".wav")]
        # file names: <emotion>/<intensity>/<speaker>-<emotion code>-<1 low|2 high>-<sentence>.wav ;
        # neutral has intensity 1 too. Female actors are picked by pitch (not by number).
        by_key: dict[tuple, list[str]] = {}
        for n in wavs:
            parts = Path(n).stem.split("-")
            spk, emo = parts[0], parts[1]
            intensity = parts[2] if len(parts) == 4 else "0"
            by_key.setdefault((spk, emo, intensity), []).append(n)
        def f0_of(n):
            y, sr = sf.read(io.BytesIO(z.read(n)))
            return f0_median(y.mean(axis=1) if y.ndim > 1 else y, sr)
        speakers = sorted({k[0] for k in by_key})
        pitch = {spk: f0_of(sorted(by_key[(spk, "N", "1")])[0]) for spk in speakers if (spk, "N", "1") in by_key}
        females = sorted(pitch, key=lambda s: -pitch[s])[:2]
        print("CaFE hauteur par comédien :", {s: round(f) for s, f in sorted(pitch.items())})
        for spk in females:
            for emo, intensity, label in (("N", "1", "neutre"), ("P", "1", "peur"), ("T", "1", "tristesse")):
                names = sorted(by_key.get((spk, emo, intensity), []))[:3]
                if not names:
                    continue
                pieces = []
                for n in names:
                    y, sr = sf.read(io.BytesIO(z.read(n)))
                    if y.ndim > 1:
                        y = y.mean(axis=1)
                    y, _ = librosa.effects.trim(y, top_db=35)
                    pieces += [y, np.zeros(int(0.35 * sr))]
                y = np.concatenate(pieces)
                out.append({"spk": spk, "emotion": label, "y": y, "sr": sr, "f0": f0_median(y, sr),
                            "snr": snr_proxy(y), "files": [Path(n).name for n in names]})
                print("CaFE", spk, label, round(out[-1]["f0"]), "Hz")
    return out


def main() -> None:
    REF.mkdir(parents=True, exist_ok=True)
    index = []
    for k, c in enumerate(mls(), 1):
        name = f"mls_f{k}"
        sf.write(REF / f"{name}.wav", normalize(librosa.resample(c["y"], orig_sr=c["sr"], target_sr=SR)), SR)
        index.append({"id": name, "kind": "adulte, livre audio", "source": "MLS French (OpenSLR 94)", "licence": "CC BY 4.0",
                      "speaker": f"lectrice MLS {c['spk']}", "book": c["book_title"], "f0_hz": round(c["f0"]),
                      "snr_db": round(c["snr"], 1), "ref_text": c["text"], "sample_rate_source": c["sr"],
                      "why": "voix féminine adulte la plus aiguë et la plus propre de cette lectrice"})
    for c in cafe():
        name = f"cafe_{c['spk']}_{c['emotion']}"
        sf.write(REF / f"{name}.wav", normalize(librosa.resample(c["y"], orig_sr=c["sr"], target_sr=SR)), SR)
        index.append({"id": name, "kind": f"adulte, comédienne, {c['emotion']}", "source": "CaFE (Gournay et al., 2018)",
                      "licence": "CC BY-NC-SA 4.0", "speaker": f"comédienne CaFE {c['spk']}", "emotion": c["emotion"],
                      "f0_hz": round(c["f0"]), "snr_db": round(c["snr"], 1), "ref_text": "", "files": c["files"],
                      "why": "référence expressive (émotion jouée par une adulte)"})
    kokoro = HERE.parent / "results" / "audio" / "ref_kokoro_child.wav"
    if kokoro.exists():
        y, sr = sf.read(kokoro)
        sf.write(REF / "synth_kokoro_child.wav", normalize(librosa.resample(y, orig_sr=sr, target_sr=SR)), SR)
        index.append({"id": "synth_kokoro_child", "kind": "synthétique (voix actuelle)", "source": "Kokoro ff_siwis ×1,25",
                      "licence": "Apache-2.0 (modèle)", "speaker": "aucun (synthèse)", "ref_text": "",
                      "why": "comparaison avec le criblage v1"})
    (REF / "references.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(index), "références")


if __name__ == "__main__":
    main()
