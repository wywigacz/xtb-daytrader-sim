"""Zrzut panelu HTML do PNG - żeby dalo się go obejrzec w prywatnym repo.

Repo jest prywatne, wiec GitHub Pages nie jest dostępne (na darmowym planie
strony są tylko publiczne). GitHub natomiast wyświetla obrazy w plikach repo,
wiec codzienny zrzut panelu jest najprostszym prywatnym "ekranem".

Uzywa Playwrighta z zainstalowana przegladarka Chrome (na runnerach GitHuba
jest gotowa), wiec nie trzeba pobierac calej przegladarki. Każdy błąd jest
niekrytyczny - symulacja ma dzialac dalej bez zrzutu.
"""
from __future__ import annotations

import os
import shutil
import sys

VIEWPORT = 1080
SCALE = 2  # retina: obraz 2160 px szerokosci, czytelny na telefonie


def _chrome_candidates() -> list[str]:
    return [
        os.environ.get("CHROME_PATH", ""),
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]


def find_browser() -> str | None:
    for c in _chrome_candidates():
        if c and os.path.exists(c):
            return c
    for name in ("google-chrome", "chromium", "chrome", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    return None


def _shrink(path: str, colors: int = 96) -> None:
    """Zmniejsz PNG bez widocznej straty: projekt jest płaski, wiec paleta
    ~96 kolorow wystarcza, a plik jest ok. 3x mniejszy (ważne dla historii git)."""
    try:
        from PIL import Image
    except ImportError:
        return
    try:
        im = Image.open(path).convert("RGB")
        im.convert("P", palette=Image.ADAPTIVE, colors=colors).save(path, optimize=True)
    except Exception as e:  # noqa: BLE001
        print("render: optymalizacja pominięta (%s)" % e, file=sys.stderr)


def to_png(html_path: str, png_path: str, width: int = VIEWPORT, scale: int = SCALE) -> bool:
    """Zwraca True, jesli zrzut powstal. Nie rzuca wyjatkiem."""
    if not os.path.exists(html_path):
        print("render: brak %s" % html_path, file=sys.stderr)
        return False
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("render: brak playwright (pip install playwright) - pomijam zrzut", file=sys.stderr)
        return False

    exe = find_browser()
    try:
        with sync_playwright() as p:
            launch = {"args": ["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"]}
            if exe:
                launch["executable_path"] = exe
            browser = p.chromium.launch(**launch)
            page = browser.new_page(
                viewport={"width": width, "height": 1400},
                device_scale_factor=scale,
            )
            page.goto("file://" + os.path.abspath(html_path), wait_until="load")
            # na obrazku linki nie dzialaja - pasek nawigacji bylby mylacy
            page.add_style_tag(content=".toc{display:none!important}")
            page.wait_for_timeout(500)
            page.screenshot(path=png_path, full_page=True)
            browser.close()
        _shrink(png_path)
        size = os.path.getsize(png_path)
        print("render: zapisano %s (%.1f kB)" % (png_path, size / 1024))
        return size > 5000
    except Exception as e:  # noqa: BLE001
        print("render: nie udało się (%s: %s)" % (type(e).__name__, e), file=sys.stderr)
        return False


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="docs/index.html")
    ap.add_argument("--out", default="docs/panel.png")
    ap.add_argument("--width", type=int, default=VIEWPORT)
    a = ap.parse_args()
    ok = to_png(a.html, a.out, a.width)
    sys.exit(0 if ok else 1)
