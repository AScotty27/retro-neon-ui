"""Render the badge and lockup PNGs from lockup.html with the kit's own fonts, plus a size-test sheet.

    python logo/tools/render_lockups.py [--work logo/tools/work] [--name "Neon App"] [--tag "Your tagline"]

Run neon_logo.py first (this reads its concept PNGs from the work folder). Serves the repo's web/ folder, the work
folder and the template on 127.0.0.1 (fonts cannot load over file://), screenshots each element with a transparent
background into the work folder, then writes badge sizes 512 down to 16 and size-test-sheet.png.
Needs Playwright for Python with Chromium: pip install playwright && python -m playwright install chromium
"""
import argparse
import posixpath
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image
from playwright.sync_api import sync_playwright

from common import REPO, TOOLS, WORK, save_png

SIZES = (512, 256, 128, 64, 48, 40, 32, 16)
ELEMENTS = ("badge-a", "badge-b", "lockup-a", "lockup-b")


class Handler(SimpleHTTPRequestHandler):
    """/web/* from the repo's web folder, /work/* from the work folder, /lockup.html from this folder."""

    def __init__(self, *args, work=None, **kwargs):
        self.work = work
        super().__init__(*args, directory=str(TOOLS), **kwargs)

    def translate_path(self, path):
        parts = [p for p in posixpath.normpath(unquote(urlsplit(path).path)).split("/") if p not in ("", ".", "..")]
        if parts[:1] == ["web"]:
            return str(REPO.joinpath("web", *parts[1:]))
        if parts[:1] == ["work"]:
            return str(self.work.joinpath(*parts[1:]))
        if parts == ["lockup.html"]:
            return str(TOOLS / "lockup.html")
        return str(TOOLS / "__not_served__")

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--work", type=Path, default=WORK, help="folder holding neon_logo.py's output")
    parser.add_argument("--name", default="Neon App", help="wordmark in the full logo (placeholder by default)")
    parser.add_argument("--tag", default="Your tagline", help="tagline under the wordmark")
    args = parser.parse_args()
    work = args.work.resolve()
    needed = [work / f"concept-{c}-transparent.png" for c in ("a-sign", "b-ident")]
    missing = [p.name for p in needed if not p.is_file()]
    if missing:
        raise SystemExit(f"FAIL: run neon_logo.py first; missing {missing} in {work}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, work=work))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 2600, "height": 1200})
            page.goto(f"http://127.0.0.1:{port}/lockup.html", wait_until="networkidle")
            page.evaluate("([name, tag]) => {"
                          " document.querySelectorAll('.lockup__name').forEach(n => n.textContent = name);"
                          " document.querySelectorAll('.lockup__tag').forEach(n => n.textContent = tag); }",
                          [args.name, args.tag])
            page.evaluate("document.fonts.ready")
            ok = page.evaluate("document.fonts.check('900 italic 100px \"Exo 2\"') && document.fonts.check('20px \"Press Start 2P\"')")
            print("kit fonts loaded:", ok)
            if not ok:
                raise SystemExit("FAIL: kit fonts did not load; the wordmark would render in a fallback font")
            broken = page.evaluate("[...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src)")
            if broken:
                raise SystemExit(f"FAIL: images did not load: {broken}")
            for element in ELEMENTS:
                # Only this element visible, so a neighbour's glow cannot bleed into the shot.
                page.evaluate("id => document.querySelectorAll('.row').forEach(r => r.style.visibility ="
                              " r.querySelector('#' + id) ? 'visible' : 'hidden')", element)
                shot_path = work / f"{element}.png"
                page.locator(f"#{element}").screenshot(path=str(shot_path), omit_background=True)
                shot = Image.open(shot_path).convert("RGBA")
                save_png(shot, shot_path)
                # Viewers that ignore alpha show glow pixels at full strength; this copy is what it looks like on black.
                black = Image.new("RGBA", shot.size, (0, 0, 0, 255))
                save_png(Image.alpha_composite(black, shot).convert("RGB"), work / f"{element}-preview-on-black.png")
                print("wrote", element + ".png (+ preview on black)")
            page.evaluate("document.querySelectorAll('.row').forEach(r => r.style.visibility = 'visible')")

            # Downscaled badges, then a sheet of them on a dark background to judge small sizes.
            for concept in ("a", "b"):
                big = Image.open(work / f"badge-{concept}.png").convert("RGBA")
                for size in SIZES:
                    save_png(big.resize((size, size), Image.LANCZOS), work / f"badge-{concept}-{size}.png")
            figures = "".join(
                f'<figure><img src="/work/badge-{c}-{s}.png" width="{s}" height="{s}"><figcaption>{c.upper()} {s}px</figcaption></figure>'
                for c in ("a", "b") for s in (128, 64, 40, 32, 16))
            page.evaluate("html => document.getElementById('sizes').innerHTML = html", figures)
            page.wait_for_function("[...document.images].every(i => i.complete && i.naturalWidth)")
            sheet = work / "size-test-sheet.png"
            page.locator("#sizes").screenshot(path=str(sheet))
            save_png(Image.open(sheet), sheet)
            print("wrote size-test-sheet.png")
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
