"""Browser checks for the web kit (web/demo/index.html) and the React layer (tests/react/smoke.html).

    python tests/check_web.py [--docs]

Serves the repo on 127.0.0.1 (random port), drives Chromium with Playwright, prints PASS/FAIL per check and exits 1
on any failure or any browser console error or page error. Screenshots go to tests/output/ (--docs: docs/screenshots/,
metadata-free). The React page needs a bundle first: cd tests/react && npm install && npm run build.
Needs: pip install playwright pillow && python -m playwright install chromium
"""
import io
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = {"width": 1440, "height": 900}
PHONE = {"width": 390, "height": 844}
SKIP_INTRO = "try { localStorage.setItem('rt-intro-seen', String(Date.now())); } catch (e) {}"
FAMILIES = ['900 italic 40px "Exo 2"', '16px "Space Grotesk"', '12px "Press Start 2P"', '20px "VT323"']

failures = []


def check(ok, what):
    print(f"{'PASS' if ok else 'FAIL'}  {what}")
    if not ok:
        failures.append(what)


class Quiet(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def shoot(page, path, full_page=False):
    """Screenshot without any PNG metadata (pixel data only)."""
    shot = Image.open(io.BytesIO(page.screenshot(full_page=full_page)))
    Image.frombytes(shot.mode, shot.size, shot.tobytes()).save(path, format="PNG", optimize=True)


def watch(page, label, errors):
    page.on("pageerror", lambda exc: errors.append(f"{label}: pageerror {exc}"))
    page.on("console", lambda msg: msg.type == "error" and errors.append(f"{label}: console {msg.text}"))


def fonts_ok(page):
    page.evaluate("document.fonts.ready")
    return page.evaluate("fs => fs.every(f => document.fonts.check(f))", FAMILIES)


def images_ok(page):
    return page.evaluate("[...document.images].every(i => i.complete && i.naturalWidth > 0)")


def demo_checks(browser, base, out, errors):
    url = f"{base}/web/demo/index.html"

    # First visit: the intro plays, hides the page, then hands over.
    context = browser.new_context(viewport=DESKTOP)
    page = context.new_page()
    watch(page, "demo/intro", errors)
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    check(page.locator(".rt-intro").count() == 1, "demo: intro plays on the first visit")
    check(page.locator("[data-rt-shell]").evaluate("n => getComputedStyle(n).opacity") == "0", "demo: page hidden while the intro plays")
    shoot(page, out / "demo-intro.png")
    page.wait_for_timeout(2600)
    check(page.locator(".rt-intro").count() == 0, "demo: intro removes itself")
    check(page.locator("[data-rt-shell]").evaluate("n => getComputedStyle(n).opacity") == "1", "demo: page visible after the intro")
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(300)
    check(page.locator(".rt-intro").count() == 0, "demo: intro does not replay on reload")
    page.goto(f"{url}?rt-intro", wait_until="domcontentloaded")
    page.wait_for_timeout(300)
    check(page.locator(".rt-intro").count() == 1, "demo: ?rt-intro forces the intro")
    page.keyboard.press("Space")
    page.wait_for_timeout(900)
    check(page.locator(".rt-intro").count() == 0, "demo: a key press skips the intro")
    context.close()

    for name, viewport in (("desktop", DESKTOP), ("phone", PHONE)):
        context = browser.new_context(viewport=viewport)
        context.add_init_script(SKIP_INTRO)
        page = context.new_page()
        watch(page, f"demo/{name}", errors)
        page.goto(url, wait_until="networkidle")
        check(fonts_ok(page), f"demo/{name}: all four kit fonts loaded")
        check(images_ok(page), f"demo/{name}: every image decoded")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check(overflow <= 0, f"demo/{name}: no horizontal scroll (overflow {overflow}px)")
        # Scroll through so every data-rt-reveal card is revealed, then back up for the shot.
        height = page.evaluate("document.documentElement.scrollHeight")
        for y in range(0, height, 500):
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(60)
        page.wait_for_timeout(700)
        hidden = page.evaluate("[...document.querySelectorAll('[data-rt-reveal]')].filter(n => !n.classList.contains('is-visible')).length")
        check(hidden == 0, f"demo/{name}: every reveal card revealed after scrolling ({hidden} left)")
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1600)
        shoot(page, out / f"demo-{name}-top.png")
        shoot(page, out / f"demo-{name}.png", full_page=True)
        context.close()

    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script(SKIP_INTRO)
    page = context.new_page()
    watch(page, "demo/behaviour", errors)
    page.goto(url, wait_until="networkidle")
    heading = page.locator("#components h2").aria_snapshot()
    check('heading "Components"' in heading and "Components Components" not in heading,
          f"demo: glitch heading read once by screen readers ({heading.strip()})")
    check(page.locator("#components h2").get_attribute("data-text") == "Components", "demo: glitch copies set up")
    check(page.locator(".rt-crt").count() == 1, "demo: CRT overlay mounted")
    check(page.locator("#form-saved").evaluate("n => getComputedStyle(n).display") == "none", "demo: [hidden] respected")
    page.click("#demo-form button[type=submit]")
    check(page.locator("#form-saved").is_visible(), "demo: form submit shows the saved alert")
    page.click("#tab-2")
    check(page.locator("#panel-2").is_visible() and not page.locator("#panel-1").is_visible(), "demo: tab click switches panels")
    page.keyboard.press("ArrowRight")
    check(page.locator("#tab-3").get_attribute("aria-selected") == "true", "demo: arrow key moves to the next tab")
    page.click("#open-dialog")
    page.wait_for_timeout(450)
    check(page.locator("#demo-dialog[open]").count() == 1, "demo: dialog opens")
    shoot(page, out / "demo-dialog.png")
    page.keyboard.press("Escape")
    check(page.locator("#demo-dialog[open]").count() == 0, "demo: Escape closes the dialog")
    page.click(".rt-nav a[href='#forms']")
    page.wait_for_timeout(100)
    check("rt-leaving" not in (page.get_attribute("html", "class") or ""), "demo: in-page links do not trigger the power-off")
    # A "leave this page?" prompt that the user cancels must not leave the page collapsed.
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.type), d.dismiss()))
    page.evaluate("window.__stay = e => { e.preventDefault(); e.returnValue = ''; };"
                  " window.addEventListener('beforeunload', window.__stay)")
    start_url = page.url
    page.click(".rt-nav a[href='./']")
    page.wait_for_timeout(1200)
    collapsed = "rt-leaving" in (page.get_attribute("html", "class") or "")
    page.keyboard.press("Shift")
    page.wait_for_timeout(100)
    back = "rt-leaving" not in (page.get_attribute("html", "class") or "")
    check(dialogs == ["beforeunload"] and page.url == start_url and back,
          f"demo: cancelled navigation powers the page back on (prompt {dialogs}, collapsed after cancel: {collapsed})")
    page.evaluate("window.removeEventListener('beforeunload', window.__stay)")
    # FX switch: off, survives a reload, hides the CRT; the script API turns it back on.
    toggle = page.locator("[data-rt-fx-slot] .rt-fx-toggle")
    check(toggle.count() == 1, "demo: FX switch placed in [data-rt-fx-slot]")
    toggle.click()
    page.reload(wait_until="networkidle")
    check("rt-fx-off" in (page.get_attribute("html", "class") or ""), "demo: FX off survives a reload")
    check(page.locator(".rt-crt").evaluate("n => getComputedStyle(n).display") == "none", "demo: CRT hidden with FX off")
    check(page.inner_text(".rt-fx-toggle") == "CRT FX OFF", "demo: switch label reads CRT FX OFF")
    page.evaluate("window.RetroNeon.setFx(true)")
    check(page.inner_text(".rt-fx-toggle") == "CRT FX ON" and page.evaluate("window.RetroNeon.fxOn()"),
          "demo: RetroNeon.setFx(true) turns FX back on and updates the switch")
    context.close()

    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce")
    page = context.new_page()
    watch(page, "demo/reduced-motion", errors)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(200)
    check(page.locator(".rt-intro").count() == 0, "demo: no intro under reduced motion")
    check(page.locator("[data-rt-shell]").evaluate("n => getComputedStyle(n).opacity") == "1", "demo: page visible under reduced motion")
    check("rt-reveal-ready" not in (page.get_attribute("html", "class") or ""), "demo: reveal cards never hidden under reduced motion")
    context.close()


def react_checks(browser, base, out, errors):
    bundle = ROOT / "tests" / "react" / "out" / "smoke.js"
    if not bundle.is_file():
        check(False, "react: bundle missing; run: cd tests/react && npm install && npm run build")
        return
    url = f"{base}/tests/react/smoke.html"

    context = browser.new_context(viewport=DESKTOP)
    page = context.new_page()
    watch(page, "react/intro", errors)
    page.goto(f"{url}?intro", wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    check(page.locator(".rt-intro").count() == 1, "react: AttractIntro plays when forced")
    check(page.locator(".rt-intro .rt-mark__name").get_attribute("data-text") == "Neon App", "react: intro name has its glitch copy")
    page.wait_for_timeout(2600)
    check(page.locator(".rt-intro").count() == 0, "react: AttractIntro removes itself")
    context.close()

    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script(SKIP_INTRO)
    page = context.new_page()
    watch(page, "react", errors)
    page.goto(url, wait_until="networkidle")
    check(page.evaluate("Boolean(window.__smoke && window.__smoke.ready)"), "react: app mounted")
    check(page.locator(".rt-intro").count() == 0, "react: intro skipped when seen recently")
    check("rt" in (page.get_attribute("html", "class") or "").split(), "react: RetroRoot put class rt on <html>")
    check(page.locator(".rt-crt").count() == 1, "react: CRT overlay mounted")
    check(fonts_ok(page), "react: kit fonts loaded")
    email = page.locator("#email")
    hint_id = email.get_attribute("aria-describedby")
    check(bool(hint_id) and page.locator(f"[id='{hint_id}']").inner_text() == "Use a full address."
          and email.get_attribute("aria-invalid") == "true", "react: Field links its hint and marks the input invalid")
    check(page.locator(".rt-progress[aria-valuenow='40']").count() == 1, "react: Progress reports its value")
    page.click("#open")
    page.wait_for_timeout(450)
    check(page.locator("dialog.rt-dialog[open]").count() == 1, "react: Dialog opens")
    page.click("#close")
    check(page.locator("dialog.rt-dialog[open]").count() == 0, "react: Dialog closes")
    page.locator(".rt-tab").first.focus()
    page.keyboard.press("ArrowRight")
    check(page.locator(".rt-tab").nth(1).get_attribute("aria-selected") == "true", "react: Tabs follow the arrow keys")
    page.click(".rt-nav a[href='#two']")
    page.wait_for_timeout(100)
    check(page.locator("#view.rt-tv-on").inner_text().startswith("VIEW TWO") or "two" in page.inner_text("#view").lower(),
          "react: PowerOn re-mounts the view on a route change")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1500)
    shoot(page, out / "react-smoke.png", full_page=True)
    page.click(".rt-fx-toggle")
    check("rt-fx-off" in (page.get_attribute("html", "class") or "") and page.inner_text(".rt-fx-toggle") == "CRT FX OFF",
          "react: FxSwitch turns FX off")
    check(page.inner_text(".rt-status") == "FX off", "react: useFx() re-renders consumers")
    page.reload(wait_until="networkidle")
    check(page.inner_text(".rt-fx-toggle") == "CRT FX OFF", "react: FX off survives a reload")

    # Two tabs of the app must not keep firing storage events at each other.
    # (A storage feedback loop can hang or kill the pages, so any exception here is a FAIL, not a crash.)
    try:
        other = context.new_page()
        watch(other, "react/second-tab", errors)
        other.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.evaluate("window.__storageEvents = 0; addEventListener('storage', () => window.__storageEvents++)")
        other.evaluate("window.__storageEvents = 0; addEventListener('storage', () => window.__storageEvents++)")
        page.wait_for_timeout(2000)
        quiet = page.evaluate("window.__storageEvents") + other.evaluate("window.__storageEvents")
        check(quiet == 0, f"react: two open tabs stay quiet ({quiet} storage events in 2 s)")
        # One tab switching FX reaches the other.
        other.click(".rt-fx-toggle")
        page.wait_for_timeout(300)
        check(page.inner_text(".rt-fx-toggle") == other.inner_text(".rt-fx-toggle") == "CRT FX ON",
              "react: FX switched in one tab updates the other")
    except Exception as error:  # noqa: BLE001
        check(False, f"react: two open tabs stay quiet (pages failed: {type(error).__name__})")
    context.close()

    # Storage blocked (private mode, sandboxed frame): the switch must still turn FX off and back on.
    context = browser.new_context(viewport=DESKTOP)
    context.add_init_script("Storage.prototype.setItem = function () { throw new Error('blocked'); };"
                            " Storage.prototype.getItem = function () { return null; };")
    page = context.new_page()
    watch(page, "react/no-storage", errors)
    page.goto(url, wait_until="networkidle")
    page.click(".rt-fx-toggle")
    off = page.inner_text(".rt-fx-toggle") == "CRT FX OFF" and "rt-fx-off" in (page.get_attribute("html", "class") or "")
    page.click(".rt-fx-toggle")
    on = page.inner_text(".rt-fx-toggle") == "CRT FX ON" and "rt-fx-off" not in (page.get_attribute("html", "class") or "")
    check(off and on, "react: FX switch works with storage blocked (off, then on again)")
    context.close()


def main():
    docs = "--docs" in sys.argv
    out = ROOT / ("docs/screenshots" if docs else "tests/output")
    out.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            # Control: the error watcher must catch a planted console error, or a clean result means nothing.
            probe = browser.new_page()
            planted = []
            watch(probe, "control", planted)
            probe.goto(f"{base}/web/demo/index.html", wait_until="domcontentloaded")
            probe.evaluate("console.error('planted control error')")
            probe.wait_for_timeout(100)
            probe.close()
            check(any("planted control error" in line for line in planted), "control: the console-error watcher catches a planted error")
            demo_checks(browser, base, out, errors)
            react_checks(browser, base, out, errors)
            browser.close()
    finally:
        server.shutdown()
    check(not errors, f"no browser console errors or page errors ({len(errors)})")
    for line in errors:
        print("   ", line)
    print(f"screenshots in {out}")
    print("ALL PASS" if not failures else f"{len(failures)} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
