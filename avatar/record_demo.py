"""Record the avatar replaying an exported session, with its voice (Playwright + ffmpeg).

    nichd-sim avatar SESSION_DIR --port 8602 &
    uv run --no-project --with playwright==1.55.0 python avatar/record_demo.py SESSION_DIR OUT.mp4 [--port 8602] [--speed 1] [--mode user|dev]

Playwright videos have no sound: the page logs when each reply starts, and the replies' WAVs are laid
on the video at those times with ffmpeg. Needs Chrome and ffmpeg (and `playwright install ffmpeg` once).
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

W, H = 1400, 860


def record(url: str, video_dir: Path, tail_s: float) -> tuple[Path, list[dict], float]:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True,
                                    args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                                          "--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(video_dir),
                                  record_video_size={"width": W, "height": H})
        created = time.time() * 1000
        page = ctx.new_page()
        page.goto(url)
        origin = page.evaluate("performance.timeOrigin")
        page.wait_for_function("window.__avatar && window.__avatar.done", timeout=30 * 60 * 1000, polling=500)
        time.sleep(tail_s)
        replies = page.evaluate("window.__avatar.replies")
        video = page.video
        ctx.close()
        browser.close()
        return Path(video.path()), replies, origin - created


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session", help="dossier exporté (performance.json + turn_NNN.wav)")
    ap.add_argument("output", help="vidéo .mp4")
    ap.add_argument("--port", type=int, default=8602)
    ap.add_argument("--speed", type=float, default=1.0, help="accélération de la vidéo finale (son compris)")
    ap.add_argument("--mode", choices=["user", "dev"], default="user",
                    help="user : salle et suivi du protocole ; dev : regard, surbrillance et carte (si exportée avec --debug-map)")
    ap.add_argument("--map", action="store_true", help="équivalent de --mode dev")
    args = ap.parse_args()
    mode = "dev" if args.map else args.mode
    session = Path(args.session)
    with tempfile.TemporaryDirectory() as tmp:
        url = f"http://127.0.0.1:{args.port}/?start=1&mode={mode}"
        webm, replies, offset = record(url, Path(tmp), tail_s=6.0 if mode == "user" else 1.5)  # user: time to read the debrief
        inputs, filters, labels = ["-i", str(webm)], [], []
        for k, r in enumerate(r for r in replies if r.get("audio")):
            delay = max(0, round(offset + r["at"]))
            inputs += ["-i", str(session / r["audio"])]
            filters.append(f"[{k + 1}:a]adelay={delay}|{delay}[a{k}]")
            labels.append(f"[a{k}]")
        cmd = ["ffmpeg", "-y", "-v", "error", *inputs]
        vf = f"setpts=PTS/{args.speed}" if args.speed != 1 else "null"
        if labels:
            af = ";".join(filters) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0[mix]"
            af += f";[mix]atempo={args.speed}[aout]" if args.speed != 1 else ";[mix]anull[aout]"
            cmd += ["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[aout]", "-c:a", "aac", "-b:a", "128k"]
        else:
            cmd += ["-vf", vf]
        cmd += ["-r", "25", "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", args.output]
        subprocess.run(cmd, check=True)
    print(json.dumps({"output": args.output, "replies": len(replies), "offset_ms": round(offset)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
