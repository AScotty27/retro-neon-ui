"""Checks for the Grafana package (grafana/).

    python tests/check_grafana.py [--docs]

Offline (always):
  1. the examples rebuild byte for byte (make_demo.py / make_linux.py + apply_theme.py vs the committed outputs);
  2. every HTML panel script parses (node, wrapped like the plugin wraps it), when node is installed;
  3. the guards bite: a changed query or a lost info note makes apply_theme fail (controls);
  4. every page rule in global.css is scoped to body.rt-grafana (or to the overlay/intro elements);
  5. panel logic: each retro panel of the demo runs in Chromium with fake Grafana data, and what it shows is checked.
Live (only when RT_GRAFANA_URL is set, plus RT_GRAFANA_USER + RT_GRAFANA_PASSWORD or RT_GRAFANA_TOKEN):
  6. creates the TestData data source (uid rt-testdata) if missing, imports the demo, opens it in Chromium and checks
     the page theme, the panels, the CRT FX switch, the intro, and that leaving the dashboard switches the theme off;
     screenshots go to tests/output/ (--docs: docs/screenshots/). Use a throwaway Grafana, never a production one.
Exit 1 on any failure.
"""
import base64
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAFANA = ROOT / "grafana"
sys.path.insert(0, str(GRAFANA / "tools"))
import apply_theme  # noqa: E402

EXAMPLES = [  # generator, source, config, committed output
    ("testdata-demo/make_demo.py", "testdata-demo/source.json", "testdata-demo/retro.json", "testdata-demo/retro-neon-demo.json"),
    ("linux-overview/make_linux.py", "linux-overview/source.json", "linux-overview/retro.json", "linux-overview/linux-overview-retro.json"),
]
failures = []


def check(ok, what):
    print(f"{'PASS' if ok else 'FAIL'}  {what}")
    if not ok:
        failures.append(what)


def html_panels(dashboard):
    return [p for p in apply_theme.all_panels(dashboard["panels"]) if p.get("type") == apply_theme.PLUGIN]


def offline():
    py = sys.executable
    for gen, src, cfg, out in EXAMPLES:
        if not (GRAFANA / "examples" / gen).exists():
            check(False, f"example generator missing: {gen}")
            continue
        # In a scratch copy of the example folder, so the tracked files are never rewritten by the check.
        folder = (GRAFANA / "examples" / gen).parent
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp) / folder.name
            shutil.copytree(folder, scratch)
            steps = [[py, str(scratch / Path(gen).name)],
                     [py, str(GRAFANA / "tools" / "apply_theme.py"), str(scratch / Path(src).name),
                      "--config", str(scratch / Path(cfg).name), "-o", str(scratch / "rebuilt.json")]]
            ran = [subprocess.run(s, capture_output=True, text=True) for s in steps]
            broken = next((r for r in ran if r.returncode != 0), None)
            if broken:
                check(False, f"{out} rebuild ran without errors: {(broken.stderr or broken.stdout).strip()[-200:]}")
                continue
            same = all((scratch / Path(p).name).read_bytes() == (GRAFANA / "examples" / p).read_bytes() for p in (src, cfg)) \
                and (scratch / "rebuilt.json").read_bytes() == (GRAFANA / "examples" / out).read_bytes()
        check(same, f"{out} rebuilds byte for byte")

    node = shutil.which("node")
    demo = json.loads((GRAFANA / "examples" / EXAMPLES[0][3]).read_text(encoding="utf-8"))
    linux = json.loads((GRAFANA / "examples" / EXAMPLES[1][3]).read_text(encoding="utf-8"))
    for name, dash in (("demo", demo), ("linux", linux)):
        for panel in html_panels(dash):
            code = "new Function('htmlNode', 'data', 'theme', 'codeData', " + json.dumps(panel["options"]["onRender"]) + ");"
            if not node:
                print(f"SKIP  {name} panel {panel['id']} syntax (node not installed)")
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(code)
            result = subprocess.run([node, f.name], capture_output=True, text=True)
            os.unlink(f.name)
            check(result.returncode == 0, f"{name} panel {panel['id']} script parses" + ("" if result.returncode == 0 else ": " + result.stderr[:200]))
    if node:  # control: the parse check must catch a broken script
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write("new Function('htmlNode', 'const x = ;');")
        result = subprocess.run([node, f.name], capture_output=True, text=True)
        os.unlink(f.name)
        check(result.returncode != 0, "control: the parse check catches a broken script")

    source = json.loads((GRAFANA / "examples" / EXAMPLES[0][1]).read_text(encoding="utf-8"))
    config = json.loads((GRAFANA / "examples" / EXAMPLES[0][2]).read_text(encoding="utf-8"))
    original = apply_theme.restyle

    def tamper_query(panel, colours):
        original(panel, colours)
        for target in panel.get("targets") or []:
            target["alias"] = "x"
            target["stringInput"] = "0"

    def tamper_note(panel, colours):
        original(panel, colours)
        panel["description"] = "changed"

    for name, fake in (("a changed query", tamper_query), ("a lost info note", tamper_note)):
        apply_theme.restyle = fake
        try:
            apply_theme.theme(copy.deepcopy(source), config)
            caught = False
        except SystemExit:
            caught = True
        finally:
            apply_theme.restyle = original
        check(caught, f"control: the guard catches {name}")

    css = (GRAFANA / "theme" / "global.css").read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    unscoped = []
    # After "}" or "{" so the first rule inside an @media / @supports block is checked too.
    # Lookbehind, so the "{" that opens an @media block is not consumed and its first rule is still found.
    for block in re.findall(r"(?:^|(?<=[{}]))\s*([^{}@][^{}]*)\{", body):
        if block.strip().startswith("@"):
            continue  # @property / @keyframes / @font-face blocks are not page rules
        for selector in block.split(","):
            s = selector.strip()
            if s and not s.startswith(("body.rt-grafana", ".rt-crt", ".rt-intro", ".rt-imark", "0%", "100%", "to", "from")) \
                    and not re.match(r"^[\d.%,\s]+$", s):
                unscoped.append(s)
    check(not unscoped, "every page rule in global.css is scoped" + (f": {unscoped[:3]}" if unscoped else ""))
    panel_logic(demo)


def frames_for(targets):
    """Fake Grafana data frames for the demo's TestData targets (the last value of each csv, the raw frames as-is)."""
    frames = []
    for t in targets:
        if t.get("scenarioId") == "csv_metric_values":
            values = [float(v) for v in t["stringInput"].split(",")]
            frames.append({"refId": t["refId"], "name": t.get("alias"), "fields": [{"name": "Time", "type": "time", "values": [0] * len(values)},
                           {"name": "Value", "type": "number", "values": values, "labels": {}}]})
        elif t.get("scenarioId") == "raw_frame":
            for frame in json.loads(t["rawFrameContent"]):
                field = frame["schema"]["fields"][0]
                frames.append({"refId": t["refId"], "fields": [{"name": field["name"], "type": "number",
                               "labels": field.get("labels", {}), "values": frame["data"]["values"][0]}]})
    return frames


def panel_logic(demo):
    from playwright.sync_api import sync_playwright
    # panel kind: (selector, "text" of the first match or "count" of matches, test, description)
    expect = {
        "hud": [("#v-0", "text", lambda s: s == "27.0%", "CPU meter shows the last value 27.0%"),
                ("#v-1", "text", lambda s: s == "27.2%", "RAM meter is the B/C ratio, 27.2%"),
                ("#h-1", "text", lambda s: s.upper() == "16.2 GIB OF 59.6 GIB", "RAM hint fills {B:bytes} of {C:bytes} (CSS shows it in caps)"),
                ("#v-5", "text", lambda s: s == "1", "services-down meter shows 1"),
                ("#hud-status-text", "text", lambda s: "1 SERVICE(S) DOWN" in s, "status line names the down service first"),
                ("#c-1", "text", lambda s: s == "UPTIME 15D 3H", "uptime chip formats a duration"),
                ("#b-0 i.on", "count", lambda n: n == 5, "CPU bar lights 5 of 20 segments for 27%")],
        "store": [(".cell", "count", lambda n: n == 4, "one cell per mount (4)"),
                  (".cell .rt-label", "text", lambda s: s == "/", "configured order puts / first"),
                  (".cell[data-state=\"warn\"]", "count", lambda n: n == 1, "the 77.4% mount is in warn")],
        "grid": [(".tile", "count", lambda n: n == 12, "one tile per target (12)"),
                 (".tile[data-state=\"down\"] .tile__name", "text", lambda s: s == "worker", "the down target sorts first"),
                 ("#grid-sum", "text", lambda s: s.startswith("11 / 12 ONLINE"), "summary 11 / 12 ONLINE")],
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        for panel in html_panels(demo):
            html = panel["options"]["html"]
            kind = "hud" if 'class="rt-panel hud"' in html else "store" if "rt-panel store" in html else "grid" if "rt-panel grid" in html else None
            if not kind:
                continue
            page.set_content("<div id='host'></div>")
            page.evaluate("""([html, css, code, frames]) => {
                const root = document.getElementById('host').attachShadow({ mode: 'open' });
                root.innerHTML = '<style>' + css + '</style>' + html;
                new Function('htmlNode', 'data', 'theme', 'codeData', code)(root, { series: frames }, { isDark: true }, {});
            }""", [html, panel["options"]["css"], panel["options"]["onRender"], frames_for(panel["targets"])])
            for selector, mode, test, what in expect[kind]:
                loc = page.locator("#host").locator(selector)
                value = loc.count() if mode == "count" else (loc.first.inner_text().strip() if loc.count() else None)
                check(bool(test(value)), f"panel logic, {kind}: {what} (got {value!r})")
            # Broken input must never throw: frames without fields, an empty series list, no data object at all.
            for broken in ({"series": [{"refId": "A"}, {"refId": "B", "fields": []}]}, {"series": []}, None):
                before = len(errors)
                page.set_content("<div id='host'></div>")
                page.evaluate("""([html, code, data]) => {
                    const root = document.getElementById('host').attachShadow({ mode: 'open' });
                    root.innerHTML = html;
                    new Function('htmlNode', 'data', 'theme', 'codeData', code)(root, data, { isDark: true }, {});
                }""", [html, panel["options"]["onRender"], broken])
                check(len(errors) == before, f"panel logic, {kind}: survives data={json.dumps(broken)[:40]}")
        check(not errors, "panel logic: no page errors" + (f": {errors[:2]}" if errors else ""))
        browser.close()


def api(base, path, auth, body=None, method=None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method or ("POST" if body is not None else "GET"))
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", auth)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode() or "{}")


def live(docs):
    base = os.environ["RT_GRAFANA_URL"].rstrip("/")
    if os.environ.get("RT_GRAFANA_TOKEN"):
        auth = "Bearer " + os.environ["RT_GRAFANA_TOKEN"]
    else:
        auth = "Basic " + base64.b64encode(f"{os.environ['RT_GRAFANA_USER']}:{os.environ['RT_GRAFANA_PASSWORD']}".encode()).decode()
    try:
        api(base, "/api/datasources/uid/rt-testdata", auth)
    except urllib.error.HTTPError:
        api(base, "/api/datasources", auth, {"name": "rt-testdata", "type": "grafana-testdata-datasource", "uid": "rt-testdata", "access": "proxy"})
    demo = json.loads((GRAFANA / "examples" / EXAMPLES[0][3]).read_text(encoding="utf-8"))
    demo["id"] = None
    saved = api(base, "/api/dashboards/db", auth, {"dashboard": demo, "overwrite": True, "message": "retro-neon-ui test"})
    check(saved.get("status") == "success", "live: demo imported")
    out = ROOT / ("docs/screenshots" if docs else "tests/output")
    out.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1600, "height": 1900}, extra_http_headers={"Authorization": auth})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
        page.on("console", lambda m: m.type == "error" and errors.append("console: " + m.text[:160]))
        page.goto(base + "/d/retro-neon-demo/x?orgId=1&rt-intro", wait_until="commit")
        page.wait_for_selector(".rt-intro", timeout=45000)
        page.wait_for_timeout(1700)
        page.screenshot(path=str(out / "grafana-intro.png"))
        page.wait_for_selector(".rt-intro", state="detached", timeout=15000)
        page.wait_for_timeout(2500)
        check("rt-grafana" in (page.get_attribute("body", "class") or ""), "live: page theme on (body.rt-grafana)")
        status = page.locator("#hud-status-text").inner_text()
        check("SERVICE(S) DOWN" in status, f"live: HUD status line from real query data ({status!r})")
        check(page.locator(".tile").count() == 12, "live: service grid has 12 tiles")
        check(page.locator(".cell").count() == 4, "live: storage cells has 4 mounts")
        check(page.locator("#v-0").inner_text().strip() not in ("", "--"), "live: CPU meter has a value")
        page.screenshot(path=str(out / "grafana-demo.png"))
        page.click("#rt-fx")
        page.wait_for_timeout(400)
        crt = page.evaluate("getComputedStyle(document.querySelector('body > .rt-crt')).display")
        check(crt == "none", "live: CRT FX switch hides the overlay")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(2500)
        check("rt-fx-off" in (page.get_attribute("body", "class") or ""), "live: FX off survives a reload")
        page.click("#rt-fx")
        page.goto(base + "/d/retro-neon-demo/x?orgId=1", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.click('[data-testid="data-testid Dashboards breadcrumb"]')
        page.wait_for_timeout(2500)
        check("rt-grafana" not in (page.get_attribute("body", "class") or ""), "live: leaving the dashboard switches the theme off")
        noise = ("api/live/ws", "cloudflareinsights", "Failed to load resource")
        real = [e for e in errors if not any(n in e for n in noise)]
        check(not real, "live: no browser errors" + (f": {real[:3]}" if real else ""))
        browser.close()


def main():
    offline()
    if os.environ.get("RT_GRAFANA_URL"):
        live("--docs" in sys.argv)
    else:
        print("SKIP  live Grafana checks (set RT_GRAFANA_URL and credentials to run them)")
    print(f"\n{'ALL PASS' if not failures else str(len(failures)) + ' FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
