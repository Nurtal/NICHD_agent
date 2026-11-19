"""Record the avatar replaying an exported session, with its voice (Playwright + ffmpeg).

    nichd-sim avatar SESSION_DIR --port 8602 &
    uv run --no-project --with playwright==1.55.0 python avatar/record_demo.py SESSION_DIR OUT.mp4 \
        [--port 8602] [--mode user|dev] [--fps 30] [--speed 1] [--realtime]

By default the page runs on a virtual clock (`?clock=manual`): each frame is rendered, screenshotted and piped
to ffmpeg, so the video has every frame however slow the renderer is, and each reply's WAV is laid exactly
where the reply starts. Chrome uses the GPU when it can (ANGLE/Vulkan), else software rendering (slower,
same video). `--realtime` keeps the old recording (Playwright screencast of the live page): it drops frames
when the renderer is slow. Needs Chrome and ffmpeg.
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
GPU_ARGS = ["--use-angle=vulkan", "--enable-features=Vulkan", "--ignore-gpu-blocklist", "--enable-gpu"]
SOFTWARE_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
RENDERER_JS = """() => { const gl = document.createElement('canvas').getContext('webgl2');
  const ext = gl && gl.getExtension('WEBGL_debug_renderer_info');
  return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : ''; }"""


def launch(p, extra: list[str]):
    """Chrome on the GPU when it is seen, else on SwiftShader. Returns (browser, renderer name)."""
    for args in (GPU_ARGS, SOFTWARE_ARGS):
        browser = p.chromium.launch(channel="chrome", headless=True, args=[*args, *extra])
        page = browser.new_page()
        renderer = page.evaluate(RENDERER_JS)
        page.close()
        if args is SOFTWARE_ARGS or (renderer and "SwiftShader" not in renderer):
            return browser, renderer
        browser.close()
    raise AssertionError("unreachable")


def record_frames(url: str, frames_out, fps: int, tail_s: float, limit_s: float | None = None) -> tuple[list[dict], int, str]:
    """Steps the virtual clock and writes one PNG per frame to `frames_out` (ffmpeg's stdin)."""
    step = 1000 / fps
    with sync_playwright() as p:
        browser, renderer = launch(p, [])
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto(url)
        page.wait_for_function("window.__avatar && window.__avatar.advance", timeout=60_000)
        n, tail, ms = 0, None, 0.0
        while True:
            r = page.evaluate("(ms) => window.__avatar.advance(ms)", 0 if n == 0 else step)
            frames_out.write(page.screenshot(type="jpeg", quality=95))
            n += 1
            if r["done"] and tail is None:
                tail = int(tail_s * fps)
            if tail is not None:
                tail -= 1
                if tail < 0:
                    break
            ms = r["now"]
            if limit_s is not None and ms >= limit_s * 1000:
                break
            if n % (fps * 10) == 0:
                print(f"  {ms / 1000:.0f} s de rejeu, {n} images", file=sys.stderr, flush=True)
        replies = page.evaluate("window.__avatar.replies")
        browser.close()
        return replies, n, renderer


def record_realtime(url: str, video_dir: Path, tail_s: float) -> tuple[Path, list[dict], float]:
    with sync_playwright() as p:
        browser, _ = launch(p, ["--autoplay-policy=no-user-gesture-required"])
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


def audio_args(session: Path, replies: list[dict], offset_ms: float, speed: float, first_input: int):
    """ffmpeg inputs and filter graph laying each reply's WAV at its start time."""
    inputs, filters, labels = [], [], []
    for k, r in enumerate(r for r in replies if r.get("audio")):
        delay = max(0, round(offset_ms + r["at"]))
        inputs += ["-i", str(session / r["audio"])]
        filters.append(f"[{first_input + k}:a]adelay={delay}|{delay}[a{k}]")
        labels.append(f"[a{k}]")
    if not labels:
        return inputs, None
    af = ";".join(filters) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0[mix]"
    af += f";[mix]atempo={speed}[aout]" if speed != 1 else ";[mix]anull[aout]"
    return inputs, af


def encode_args(output: str, fps: int) -> list[str]:
    return ["-r", str(fps), "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", output]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session", help="dossier exporté (performance.json + turn_NNN.wav)")
    ap.add_argument("output", help="vidéo .mp4")
    ap.add_argument("--port", type=int, default=8602)
    ap.add_argument("--speed", type=float, default=1.0, help="accélération de la vidéo finale (son compris)")
    ap.add_argument("--mode", choices=["user", "dev"], default="user",
                    help="user : salle et suivi du protocole ; dev : regard, surbrillance et carte (si exportée avec --debug-map)")
    ap.add_argument("--map", action="store_true", help="équivalent de --mode dev")
    ap.add_argument("--fps", type=int, default=30, help="images par seconde (capture image par image)")
    ap.add_argument("--limit", type=float, help="s'arrêter après ce nombre de secondes de rejeu (aperçu)")
    ap.add_argument("--realtime", action="store_true",
                    help="ancien enregistrement en temps réel (perd des images si le rendu est lent)")
    args = ap.parse_args()
    mode = "dev" if args.map else args.mode
    session = Path(args.session)
    tail_s = 6.0 if mode == "user" else 1.5  # user: time to read the debrief
    vf = f"setpts=PTS/{args.speed}" if args.speed != 1 else "null"

    if args.realtime:
        with tempfile.TemporaryDirectory() as tmp:
            webm, replies, offset = record_realtime(f"http://127.0.0.1:{args.port}/?start=1&mode={mode}", Path(tmp), tail_s)
            inputs, af = audio_args(session, replies, offset, args.speed, first_input=1)
            cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(webm), *inputs]
            cmd += (["-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[aout]", "-c:a", "aac", "-b:a", "128k"]
                    if af else ["-vf", vf])
            subprocess.run([*cmd, *encode_args(args.output, 25)], check=True)
        print(json.dumps({"output": args.output, "replies": len(replies), "offset_ms": round(offset)}))
        return 0

    # frame by frame: video first (frames piped in), then the voice laid on it
    started = time.time()
    url = f"http://127.0.0.1:{args.port}/?start=1&clock=manual&mode={mode}"
    with tempfile.TemporaryDirectory() as tmp:
        silent = Path(tmp) / "video.mp4"
        ffmpeg = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(args.fps),
                                   "-i", "-", "-vf", vf, *encode_args(str(silent), args.fps)], stdin=subprocess.PIPE)
        try:
            replies, frames, renderer = record_frames(url, ffmpeg.stdin, args.fps, tail_s, args.limit)
        finally:
            ffmpeg.stdin.close()
            ffmpeg.wait()
        if ffmpeg.returncode:
            raise SystemExit(f"ffmpeg a échoué ({ffmpeg.returncode})")
        inputs, af = audio_args(session, replies, 0, args.speed, first_input=1)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(silent), *inputs]
        if af:
            cmd += ["-filter_complex", af, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", args.output]
        else:
            cmd += ["-c", "copy", "-movflags", "+faststart", args.output]
        subprocess.run(cmd, check=True)
    print(json.dumps({"output": args.output, "replies": len(replies), "frames": frames, "fps": args.fps,
                      "renderer": renderer, "seconds": round(time.time() - started)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
