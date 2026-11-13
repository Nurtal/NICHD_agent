"""Build slides.pdf from slides.html with headless Chrome.

Usage (from this folder): uv run --no-project --with playwright python build_pdf.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto((HERE / "slides.html").as_uri())
    page.wait_for_load_state("networkidle")
    page.pdf(path=str(HERE / "slides.pdf"), width="1280px", height="720px", print_background=True,
             prefer_css_page_size=True)
    browser.close()
print("slides.pdf written")
