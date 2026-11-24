"""Record the demo of the model control panel (view « Règles du modèle »), Playwright, system Chrome, headless.

1. Start the UI offline (no LLM needed), with a scratch presets folder:
       NICHD_OFFLINE=1 NICHD_PRESETS=/tmp/presets uv run streamlit run src/nichd_sim/ui/app.py \
           --server.address 127.0.0.1 --server.port 8611 --server.headless true
2. Record (webm in OUT_DIR), then convert:
       uv run --no-project --with playwright==1.55.0 python docs/presentation/record_rules_demo.py OUT_DIR [--url URL]
       ffmpeg -i OUT_DIR/*.webm -r 25 -c:v libx264 -crf 26 -pix_fmt yuv420p demo-regles-du-modele.mp4

Scenario s01 (Léo, 5 ans), seed 0. Walkthrough: the catalogue, search, sources, switching off the gaze-aversion
rule, adjusting a slider, saving a preset, an interview played with it (live engine view), reset and reload.
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
URL = sys.argv[sys.argv.index("--url") + 1] if "--url" in sys.argv else "http://127.0.0.1:8611"
W, H = 1600, 1000
PRESET = "Démo sans regard de mémoire"

CAPTION_JS = """(text) => {
  let el = document.getElementById('demo-caption');
  if (!el) {
    el = document.createElement('div');
    el.id = 'demo-caption';
    el.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;' +
      'background:rgba(20,24,33,.88);color:#fff;font:500 21px/1.35 system-ui,sans-serif;padding:12px 22px;' +
      'border-radius:12px;max-width:1100px;text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.25);' +
      'transition:opacity .3s';
    document.body.appendChild(el);
  }
  el.style.opacity = text ? 1 : 0;
  if (text) el.textContent = text;
}"""


def wait_idle(page, timeout=60):
    t0 = time.time()
    time.sleep(0.6)
    while time.time() - t0 < timeout:
        if not page.locator('[data-testid="stStatusWidget"]').count():
            return
        time.sleep(0.2)


def caption(page, text, hold=2.5):
    page.evaluate(CAPTION_JS, text)
    time.sleep(hold)


def scroll(page, dy, speed=60):
    box = page.locator('[data-testid="stMain"]').bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.6, box["y"] + 450)
    for _ in range(abs(dy) // speed):
        page.mouse.wheel(0, speed if dy > 0 else -speed)
        time.sleep(0.03)
    time.sleep(0.6)


def to_top(page):
    page.locator('[data-testid="stMain"]').evaluate("el => el.scrollTo({top: 0, behavior: 'smooth'})")
    time.sleep(1.0)


def view(page, name):
    page.locator('[data-testid="stMain"]').get_by_text(name, exact=True).first.click()
    wait_idle(page)


def search(page, text):
    box = page.get_by_placeholder("regard, suggestion, mensonge…")
    box.fill("")
    box.press_sequentially(text, delay=90)
    box.press("Enter")
    wait_idle(page)


def card(page, title):
    return (page.locator('[data-testid="stVerticalBlock"]').filter(has_text=title)
            .filter(has_text="Sources et réglages avancés").last)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": W, "height": H}, locale="fr-FR",
                                  record_video_dir=str(OUT), record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        page.goto(URL)
        page.wait_for_selector('[data-testid="stSidebar"]')
        wait_idle(page)
        time.sleep(1)

        caption(page, "Panneau de configuration du modèle : les règles qui dirigent le comportement de l'enfant", 2)
        view(page, "Règles du modèle")
        caption(page, "44 règles tirées de la littérature, en 8 familles — 36 se désactivent, toutes se règlent", 3)
        scroll(page, 2400, speed=40)
        caption(page, "Chaque carte : la règle en « si… alors… », son niveau de preuve, ses curseurs", 3)
        to_top(page)

        caption(page, "Rechercher une règle : « regard »", 0.5)
        search(page, "regard")
        scroll(page, 380)
        caption(page, "« Regard détourné pendant l'effort de mémoire » (Doherty-Sneddon & Phelps, 2005)", 2.5)
        gaze = card(page, "Regard détourné pendant l'effort de mémoire")
        gaze.get_by_text("Sources et réglages avancés").click()
        wait_idle(page)
        caption(page, "Les sources, avec leur lien DOI, et l'origine de chaque valeur", 4)
        gaze.get_by_text("Sources et réglages avancés").click()
        wait_idle(page)

        caption(page, "Décocher la règle : elle s'éteint et ses curseurs se grisent", 1.2)
        gaze.get_by_text("Regard détourné pendant l'effort de mémoire").first.click()
        wait_idle(page)
        time.sleep(2)

        caption(page, "Régler un coefficient : le biais du « oui » chez les 4–6 ans", 0.5)
        search(page, "oui")
        scroll(page, 380)
        slider = page.locator('[data-testid="stSlider"]').filter(has_text="Faux « oui »").get_by_role("slider")
        slider.focus()
        for _ in range(6):
            slider.press("ArrowRight")
            time.sleep(0.25)
        wait_idle(page)
        caption(page, "✎ signale une valeur modifiée ; la valeur par défaut reste dans l'aide", 3)

        to_top(page)
        caption(page, "Enregistrer la configuration dans un préréglage nommé", 0.5)
        page.get_by_placeholder("ex. enfant-tres-suggestible").press_sequentially(PRESET, delay=60)
        page.get_by_placeholder("ex. enfant-tres-suggestible").press("Enter")
        wait_idle(page)
        page.get_by_role("button", name="Enregistrer").click()
        wait_idle(page)
        caption(page, "Le compteur et la barre latérale résument la configuration", 3)

        caption(page, "« Nouvel entretien » : les réglages s'appliquent et sont écrits dans le journal", 1)
        page.get_by_role("button", name="Nouvel entretien").click()
        wait_idle(page)
        view(page, "Moteur en direct")
        chat = page.get_by_placeholder("Votre énoncé…").first
        chat.press_sequentially("[dir:d_pousse] Qui a poussé le monsieur ?", delay=45)
        chat.press("Enter")
        wait_idle(page)
        caption(page, "La vue « Moteur en direct » rappelle les règles de cet entretien", 4)
        caption(page, "Le journal garde la configuration et le profil : l'entretien se rejoue à l'identique", 3.5)

        view(page, "Règles du modèle")
        caption(page, "Réinitialiser : toutes les règles actives, valeurs par défaut", 1)
        page.get_by_role("button", name="Réinitialiser").click()
        wait_idle(page)
        time.sleep(1.5)
        caption(page, "Recharger le préréglage enregistré", 0.8)
        page.locator('[data-testid="stSelectbox"]').filter(has_text="Préréglage").click()
        page.get_by_role("option").filter(has_text="sans-regard").first.click()
        wait_idle(page)
        page.get_by_role("button", name="Charger").click()
        wait_idle(page)
        caption(page, "La configuration revient : 35 / 36 règles actives, 1 paramètre modifié", 4)
        caption(page, "", 0.8)
        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
