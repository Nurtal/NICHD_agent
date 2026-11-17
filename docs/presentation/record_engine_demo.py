"""Record the live engine view demo (Playwright, system Chrome, headless).

1. Start the UI on port 8599 (real local model, Ollama running):
       uv run streamlit run src/nichd_sim/ui/app.py --server.address 127.0.0.1 --server.port 8599 --server.headless true
2. Record (webm in OUT_DIR), then convert:
       uv run --no-project --with playwright python docs/presentation/record_engine_demo.py OUT_DIR [--shots]
       ffmpeg -i OUT_DIR/*.webm -vf "setpts=0.5*PTS" -r 25 -c:v libx264 -crf 27 -pix_fmt yuv420p demo-x2.mp4
   --shots: screenshots at each step instead of a video (to check the layout).
   --graph: the "Graphe du système" view (live system map) instead of "Moteur en direct".
   The first video run may need `playwright install ffmpeg`.

Scenario s02 (Emma, 8), reluctance lowered to 0.10 from the sidebar, seed 0, 8 turns: rapport, ground
rule, transition, free recall, suggestive, forced choice, support, facilitator.
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8599"
OUT = Path(sys.argv[1])
SHOTS = "--shots" in sys.argv
GRAPH = "--graph" in sys.argv  # the system map view instead of the live engine view
W, H = 1600, 1000

TURNS = [
    "Bonjour Emma, je m'appelle Claire. Qu'est-ce que tu aimes faire quand tu joues ?",
    "Si tu ne sais pas la réponse à une question, tu peux me dire « je ne sais pas ».",
    "Dis-moi pourquoi tu es venue me voir aujourd'hui.",
    "Raconte-moi tout ce qui s'est passé, depuis le début.",
    "Il t'a serré le cou, c'est ça ?",
    "C'était le soir ou le matin ?",
    "Tu fais du très bon travail, merci de m'expliquer tout ça.",
    "Et ensuite, qu'est-ce qui s'est passé ?",
]


def wait_idle(page, timeout=180):
    """Wait until Streamlit has finished running (no spinner, not 'running')."""
    t0 = time.time()
    time.sleep(0.8)
    while time.time() - t0 < timeout:
        running = page.locator('[data-testid="stStatusWidget"]').count()
        spinner = page.locator('[data-testid="stSpinner"]').count()
        if not running and not spinner:
            return
        time.sleep(0.3)


def engine_scroll(page, dy):
    box = page.locator('[data-testid="stMain"]').bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.7, box["y"] + 400)
    for _ in range(abs(dy) // 100):
        page.mouse.wheel(0, 100 if dy > 0 else -100)
        time.sleep(0.04)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx_kw = {"viewport": {"width": W, "height": H}, "locale": "fr-FR"}
        if not SHOTS:
            ctx_kw["record_video_dir"] = str(OUT)
            ctx_kw["record_video_size"] = {"width": W, "height": H}
        ctx = browser.new_context(**ctx_kw)
        page = ctx.new_page()
        page.goto(URL)
        page.wait_for_selector('[data-testid="stSidebar"]')
        wait_idle(page)
        time.sleep(1.5)

        # Scenario + profile
        page.locator('[data-testid="stSelectbox"]').first.click()
        page.get_by_role("option", name="Emma, 8 ans — violences physiques à la maison", exact=True).click()
        wait_idle(page)
        time.sleep(1)
        page.get_by_text("Profil de l'enfant").click()
        time.sleep(0.8)
        thumb = page.locator('[data-testid="stSidebar"] input[type="range"]').first
        thumb.focus()
        for _ in range(11):  # 0.65 → 0.10
            page.keyboard.press("ArrowLeft")
            time.sleep(0.15)
        wait_idle(page)
        time.sleep(1)
        if SHOTS:
            page.screenshot(path=str(OUT / "0_sidebar.png"))
        page.get_by_role("button", name="Nouvel entretien").click()
        wait_idle(page)
        page.get_by_text("Graphe du système" if GRAPH else "Moteur en direct").click()
        if GRAPH:  # more room for the map
            wait_idle(page)
            page.locator('[data-testid="stSidebar"]').hover()
            page.locator('[data-testid="stSidebarCollapseButton"] button').first.click(force=True)
            time.sleep(1)
        wait_idle(page)
        time.sleep(1.5)

        for i, text in enumerate(TURNS):
            box = page.locator('textarea[data-testid="stChatInputTextArea"]')
            box.click()
            box.type(text, delay=18)
            time.sleep(0.4)
            box.press("Enter")
            if GRAPH:  # the map lights up while the turn runs: just watch it
                if SHOTS:
                    for k, dt in enumerate((1.0, 2.0, 3.0)):
                        time.sleep(dt)
                        page.screenshot(path=str(OUT / f"{i + 1}_live{k}.png"))
                wait_idle(page)
                time.sleep(2.5)
                if SHOTS:
                    page.screenshot(path=str(OUT / f"{i + 1}_done.png"))
                continue
            wait_idle(page)
            engine_scroll(page, -4000)  # state and trajectory first
            time.sleep(2.5)
            if SHOTS:
                page.screenshot(path=str(OUT / f"{i + 1}_top.png"))
            engine_scroll(page, 700)  # then the steps of the turn
            time.sleep(2.5)
            if SHOTS:
                page.screenshot(path=str(OUT / f"{i + 1}_steps.png"))
            engine_scroll(page, 600)
            time.sleep(2.0)
            if SHOTS:
                page.screenshot(path=str(OUT / f"{i + 1}_bottom.png"))
            engine_scroll(page, -4000)
            time.sleep(0.6)
        time.sleep(2)
        video = page.video
        ctx.close()
        browser.close()
        if video:
            print(video.path())


if __name__ == "__main__":
    main()
