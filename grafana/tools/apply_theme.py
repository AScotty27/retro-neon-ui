"""Give any Grafana dashboard the retro-neon-ui look. Reads an exported dashboard JSON, writes a themed copy.

    python grafana/tools/apply_theme.py IN.json -o OUT.json [--config retro.json] [--native-only] [--uid UID]

What it does (presentation only; every query and every panel's info note is kept, and the build fails if not):
- native panels: neon colours for Grafana's named colours, 2 px glowing lines, LCD bar gauges, neon state timelines;
  per-series colours from the config; by-value colour schemes (green-yellow-red) are kept, the colour IS the data;
- unless --native-only: one HTML Graphics panel at the top carries the page theme (dark chrome, stripe-capped
  panels, neon titles, CRT scanlines, CRT FX switch, optional attract-mode intro), scoped to this dashboard's URL;
- config "add": retro panels inserted at the top (status-hud, storage-cells, service-grid, banner), others moved down;
- config "replace": existing panels turned into a retro panel kind, keeping their queries, notes and position.
Needs the "HTML Graphics" panel plugin (gapit-htmlgraphics-panel, 2.2 or later) unless --native-only.
Config reference and examples: grafana/README.md, grafana/examples/.
"""
import argparse
import base64
import copy
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAFANA = ROOT / "grafana"
PANELS = GRAFANA / "panels"
FONTS = ROOT / "web" / "fonts"
PLUGIN = "gapit-htmlgraphics-panel"

NEON = {
    "green": "#5dff8f", "semi-dark-green": "#5dff8f", "dark-green": "#3ad977", "light-green": "#9dff2e",
    "super-light-green": "#b8ffc9", "red": "#ff4d5e", "semi-dark-red": "#ff4d5e", "dark-red": "#ff2e5e",
    "light-red": "#ff7a8a", "super-light-red": "#ffb3ba", "yellow": "#ffd60a", "semi-dark-yellow": "#ffd60a",
    "dark-yellow": "#ffc400", "light-yellow": "#ffef5c", "super-light-yellow": "#fff6a0", "orange": "#ff8c1a",
    "semi-dark-orange": "#ff8c1a", "dark-orange": "#ff7a00", "light-orange": "#ffa94d", "super-light-orange": "#ffc98a",
    "blue": "#4d5bff", "semi-dark-blue": "#4d5bff", "dark-blue": "#3d4dff", "light-blue": "#2de2ff",
    "super-light-blue": "#8ff0ff", "purple": "#a63dff", "semi-dark-purple": "#a63dff", "dark-purple": "#8a2be2",
    "light-purple": "#c77dff", "super-light-purple": "#ddb3ff",
}
FONT_FACES = [  # family, file, style, weight
    ("Exo 2", "exo2-italic.woff2", "italic", "400 900"),
    ("Space Grotesk", "space-grotesk.woff2", "normal", "400 700"),
    ("Press Start 2P", "press-start-2p.ttf", "normal", "400"),
    ("VT323", "vt323.woff2", "normal", "400"),
]
KINDS = {  # kind: (css files, js files)
    "status-hud": (["status-hud.css"], ["status-hud.js", "fx-switch.js"]),
    "storage-cells": (["storage-cells.css"], ["storage-cells.js"]),
    "service-grid": (["service-grid.css"], ["service-grid.js"]),
    "banner": (["banner.css"], ["banner.js", "fx-switch.js"]),
}
STRIPES = '<span class="rt-mark__stripes"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></span>'
RING = '<svg viewBox="0 0 100 100" focusable="false"><circle cx="50" cy="50" r="46"></circle></svg>'
FX_BUTTON = '<button class="hud__fx" id="rt-fx" type="button" aria-pressed="true">CRT FX ON</button>'


def fail(message):
    raise SystemExit("FAIL: " + message)


def read(name):
    return (PANELS / name).read_text(encoding="utf-8")


def esc(text):
    return html.escape(str(text or ""), quote=True)


# ---------- page theme ----------

def font_faces():
    out = []
    for family, file, style, weight in FONT_FACES:
        data = base64.b64encode((FONTS / file).read_bytes()).decode("ascii")
        mime, fmt = ("font/ttf", "truetype") if file.endswith(".ttf") else ("font/woff2", "woff2")
        out.append(f'@font-face {{ font-family: "{family}"; font-style: {style}; font-weight: {weight}; '
                   f'font-display: swap; src: url(data:{mime};base64,{data}) format("{fmt}"); }}')
    return "\n".join(out)


def runtime(uids, intro):
    css = (GRAFANA / "theme" / "global.css").read_text(encoding="utf-8").replace("/*__FONTS__*/", font_faces())
    # One line: the CSS travels inside a JS string inside JSON, and line breaks there become "\n" escapes.
    css = re.sub(r"\s*\n\s*", " ", css).strip()
    js = (GRAFANA / "theme" / "runtime.js").read_text(encoding="utf-8")
    version = "rt-grafana-" + hashlib.sha1((css + js).encode("utf-8")).hexdigest()[:12]
    for token, value in (("__RT_VERSION__", version), ("__RT_DASH_UIDS__", list(uids)),
                         ("__RT_INTRO__", intro or None), ("__RT_GLOBAL_CSS__", css)):
        if js.count(token) != 1:
            fail(f"runtime.js placeholder {token} found {js.count(token)} times")
        js = js.replace(token, json.dumps(value))
    return js


# ---------- retro panel kinds (HTML) ----------

def mark(cfg, size_class):
    logo = cfg.get("logo")
    first = (cfg.get("title") or "?")[:1]
    # A "$variable" title is filled in by the panel script, which also sets the glyph.
    inner = f'<img src="{esc(logo)}" alt="">' if logo else \
        f'<span class="rt-mark__glyph">{esc("" if first == "$" else first.upper())}</span>'
    return f'<div class="rt-mark {size_class}" aria-hidden="true">{STRIPES}<span class="rt-mark__ring">{RING}{inner}</span></div>'


def html_for(kind, cfg, fallback_title):
    title = cfg.get("title") or fallback_title or ""
    if kind == "banner":
        kicker = f'<div class="rt-label">{esc(cfg["kicker"])}</div>' if cfg.get("kicker") else ""
        return (f'<div class="rt-panel rt-box banner">{mark(dict(cfg, title=title), "banner__mark")}'
                f'<div class="banner__titles">{kicker}<div class="banner__title rt-glitch" data-text="{esc(title)}">'
                f'{esc(title)}</div></div>{FX_BUTTON}</div>')
    if kind == "status-hud":
        meters = cfg.get("meters") or []
        if not meters:
            fail("status-hud needs at least one meter")
        cards = "".join(
            f'<article class="rt-box meter" id="m-{i}"><div class="rt-label">{esc(m.get("label"))}</div>'
            f'<div class="meter__value" id="v-{i}">--</div><div class="meter__bar" id="b-{i}"></div>'
            f'<div class="meter__hint" id="h-{i}">{esc(m.get("hint") if "{" not in str(m.get("hint", "")) else "")}</div></article>'
            for i, m in enumerate(meters))
        chips = "".join(f'<span class="hud__chip" id="c-{i}">--</span>' for i, _ in enumerate(cfg.get("chips") or []))
        kicker = f'<div class="rt-label hud__kicker">{esc(cfg["kicker"])}</div>' if cfg.get("kicker") else ""
        return (f'<div class="rt-panel hud" id="hud" style="--rt-cols: {min(len(meters), 6)}">'
                f'<header class="rt-box hud__top">{mark(dict(cfg, title=title), "hud__mark")}'
                f'<div class="hud__titles">{kicker}<div class="hud__title rt-glitch" data-text="{esc(title)}">{esc(title)}</div>'
                f'<div class="hud__status" id="hud-status" data-level="ok" aria-live="polite"><span id="hud-status-text">'
                f'&gt; READING SENSORS</span><span class="hud__cursor" aria-hidden="true"></span></div></div>'
                f'<div class="hud__side"><div class="hud__chips">{chips}</div>{FX_BUTTON}</div></header>'
                f'<section class="hud__grid">{cards}</section></div>')
    if kind == "storage-cells":
        sub = f'<div class="store__sub">{esc(cfg["subtitle"])}</div>' if cfg.get("subtitle") else ""
        return (f'<div class="rt-panel store"><header class="store__head"><div class="store__title">{esc(title)}</div>'
                f'<span class="store__trail" aria-hidden="true"></span>{sub}</header>'
                f'<section class="store__grid" id="cells"></section></div>')
    if kind == "service-grid":
        return (f'<div class="rt-panel grid"><header class="grid__head"><div class="grid__title">{esc(title)}</div>'
                f'<span class="grid__trail" aria-hidden="true"></span><div class="grid__sum" id="grid-sum" data-level="ok">'
                f'--</div></header><section class="grid__tiles" id="grid-tiles" aria-live="polite"></section></div>')
    fail(f"unknown panel kind {kind!r} (use one of {sorted(KINDS)})")


def retro_panel(template, kind, cfg, fallback_title, carrier_js=""):
    css_files, js_files = KINDS[kind]
    js = "\n".join(read(f) for f in js_files)
    if js.count("__RT_PANEL_CONFIG__") > 1:
        fail(f"{kind}: config placeholder used more than once")
    js = js.replace("__RT_PANEL_CONFIG__", json.dumps(cfg))
    panel = copy.deepcopy(template)
    panel["type"] = PLUGIN
    panel["transparent"] = True
    panel["title"] = ""
    panel["options"] = {
        "html": html_for(kind, cfg, fallback_title),
        "css": read("panel-base.css") + "\n" + "\n".join(read(f) for f in css_files),
        "onRender": (carrier_js + "\n" if carrier_js else "") + js,
        "onInit": "// rendering happens in onRender",
        "codeData": "{}", "rootCSS": "", "overflow": "hidden", "centerAlignContent": False,
        "add100Percentage": True, "useGrafanaScrollbar": True, "renderOnMount": True, "panelupdateOnMount": True,
        "onInitOnResize": False, "SVGBaseFix": True, "dynamicData": False, "dynamicHtmlGraphics": False,
        "dynamicFieldDisplayValues": False, "dynamicProps": False, "calcsMutation": "standard",
        "reduceOptions": {"calcs": ["lastNotNull"]},
    }
    panel.pop("fieldConfig", None)
    panel["fieldConfig"] = {"defaults": {}, "overrides": []}
    for key in ("pluginVersion", "libraryPanel"):
        panel.pop(key, None)
    return panel


# ---------- native panels ----------

def recolour(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("color", "fixedColor") and isinstance(value, str) and value in NEON:
                node[key] = NEON[value]
            else:
                recolour(value)
    elif isinstance(node, list):
        for item in node:
            recolour(item)


def restyle(panel, series_colours):
    kind = panel.get("type")
    fc = panel.setdefault("fieldConfig", {"defaults": {}, "overrides": []})
    defaults = fc.setdefault("defaults", {})
    if kind == "timeseries":
        custom = defaults.setdefault("custom", {})
        if custom.get("drawStyle", "line") == "line":
            custom.update({"lineWidth": max(2, custom.get("lineWidth", 1)), "showPoints": "never",
                           "fillOpacity": max(16, custom.get("fillOpacity", 0))})
            # A "scheme" gradient colours the line by value (the colour is the data): keep it.
            if custom.get("gradientMode") != "scheme":
                custom["gradientMode"] = "opacity"
    elif kind == "bargauge":
        panel.setdefault("options", {}).update({"displayMode": "lcd", "valueMode": "color", "showUnfilled": True})
    elif kind in ("state-timeline", "status-history"):
        # Solid neon bars; the value text in the bars goes (the colour and the tooltip carry it).
        defaults.setdefault("custom", {})["fillOpacity"] = 85
        panel.setdefault("options", {})["showValue"] = "never"
    for name, colour in (series_colours or {}).items():
        fc.setdefault("overrides", []).append({"matcher": {"id": "byName", "options": name},
                                               "properties": [{"id": "color", "value": {"mode": "fixed", "fixedColor": colour}}]})
    recolour(fc)


# ---------- the dashboard ----------

def all_panels(panels):
    for p in panels:
        yield p
        yield from all_panels(p.get("panels") or [])


def target_signature(panel):
    keys = ("refId", "expr", "query", "rawSql", "legendFormat", "instant", "range", "format", "interval",
            "intervalFactor", "hide", "scenarioId", "stringInput", "rawFrameContent", "labels", "seriesCount")
    return sorted(json.dumps([t.get(k) for k in keys] + [panel.get("datasource")], sort_keys=True)
                  for t in panel.get("targets") or [])


def theme(dashboard, cfg, native_only=False, uid=None, copy_uid=None):
    src = copy.deepcopy(dashboard)
    dash = copy.deepcopy(dashboard)
    if any(p.get("type") == PLUGIN and "__rtGrafana" in str((p.get("options") or {}).get("onRender", ""))
           for p in all_panels(dash.get("panels") or [])):
        fail("this dashboard is already themed (it has the retro runtime); theme the original export instead")
    if copy_uid:  # import as a copy: new uid (the page theme is scoped to it) and a marked title
        dash["uid"], dash["title"] = copy_uid, (dash.get("title") or "Dashboard") + " (retro)"
        dash["id"] = None
    # --uid only fills a missing uid; changing an existing one is an edit to the file, made on purpose.
    if uid and dash.get("uid") and uid != dash["uid"]:
        fail(f"the dashboard already has uid {dash['uid']!r}; to import it as a copy, change uid in the file")
    uid = dash.get("uid") or uid
    if not uid and not native_only:
        fail("the dashboard has no uid; pass --uid (the page theme is scoped to /d/<uid>)")
    if uid:
        dash["uid"] = uid
    # From the untouched copy: the guards below must compare against the input, not against panels being edited.
    originals = {p["id"]: p for p in all_panels(src.get("panels") or []) if "id" in p}
    replace = {int(k): v for k, v in (cfg.get("replace") or {}).items()}
    for pid, spec in replace.items():
        if pid not in originals:
            fail(f"replace: no panel with id {pid}")
        if (spec or {}).get("kind") not in KINDS:
            fail(f"replace {pid}: unknown kind {(spec or {}).get('kind')!r} (use one of {sorted(KINDS)})")
        if originals[pid].get("transformations"):
            fail(f"replace {pid}: the panel has transformations, which reshape the frames the retro panel reads; "
                 "use 'add' with its own queries instead")

    # 1. restyle or replace the existing panels, in place
    def walk(panels):
        out = []
        for p in panels:
            if p.get("id") in replace and not native_only:
                spec = replace[p["id"]]
                new = retro_panel(p, spec["kind"], spec.get("config") or {}, p.get("title"))
                new["description"] = p.get("description", "")
                out.append(new)
                continue
            restyle(p, (cfg.get("seriesColors") or {}).get(str(p.get("id"))))
            if p.get("panels"):
                p["panels"] = walk(p["panels"])
            out.append(p)
        return out
    dash["panels"] = walk(dash.get("panels") or [])

    # 2. new retro panels at the top; the first one also carries the page runtime
    if not native_only:
        add = list(cfg.get("add") or [])
        if not add:
            add = [{"kind": "banner", "height": 3, "config": cfg.get("banner") or {}}]
        next_id = max([p.get("id", 0) for p in all_panels(dash["panels"])] + [0]) + 1
        top, new_panels = 0, []
        datasource = next((p.get("datasource") for p in originals.values() if p.get("datasource")), None)
        for i, spec in enumerate(add):
            kind = spec.get("kind")
            if kind not in KINDS:
                fail(f"add: unknown kind {kind!r}")
            carrier = runtime([uid] + list(cfg.get("extraUids") or []), cfg.get("intro")) if i == 0 else ""
            template = {"datasource": spec.get("datasource", datasource), "targets": copy.deepcopy(spec.get("targets") or [])}
            panel = retro_panel(template, kind, spec.get("config") or {}, dash.get("title"), carrier)
            height = int(spec.get("height") or {"banner": 3, "status-hud": 11, "storage-cells": 7, "service-grid": 10}[kind])
            panel.update({"id": next_id, "gridPos": {"x": 0, "y": top, "w": 24, "h": height},
                          "description": spec.get("description", "")})
            if not panel["targets"]:
                panel.pop("datasource", None)
            next_id += 1
            top += height
            new_panels.append(panel)
        # Move every existing panel down, including the ones stored inside collapsed rows.
        for p in all_panels(dash["panels"]):
            pos = p.setdefault("gridPos", {"x": 0, "y": 0, "w": 24, "h": 8})
            pos["y"] = pos.get("y", 0) + top
        dash["panels"] = new_panels + dash["panels"]
        added_ids = {p["id"] for p in new_panels}
    else:
        added_ids = set()

    # 3. guards: every query and every info note survives
    before = sorted(s for p in all_panels(src.get("panels") or []) for s in target_signature(p))
    after = sorted(s for p in all_panels(dash["panels"]) if p.get("id") not in added_ids for s in target_signature(p))
    if before != after:
        fail("a query was lost or changed")
    kept = {p.get("id"): p for p in all_panels(dash["panels"])}
    for pid, p in originals.items():
        if (p.get("description") or "") != (kept.get(pid, {}).get("description") or ""):
            fail(f"panel {pid} lost its info note")
    note = "Retro neon theme by retro-neon-ui (grafana/tools/apply_theme.py)."
    dash["description"] = (note + " " + (src.get("description") or "")).strip() if note not in (src.get("description") or "") \
        else src.get("description")
    return dash


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--config", help="retro config JSON (see grafana/README.md)")
    ap.add_argument("--native-only", action="store_true", help="colours and LCD only; no HTML panels, no page theme")
    ap.add_argument("--uid", help="dashboard uid when the export has none")
    ap.add_argument("--copy", metavar="NEW_UID", help="output a copy: this new uid, ' (retro)' on the title, no id")
    args = ap.parse_args(argv)
    doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
    dashboard = doc["dashboard"] if isinstance(doc.get("dashboard"), dict) else doc
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    themed = theme(dashboard, cfg, args.native_only, args.uid, args.copy)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(themed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    html_panels = sum(1 for p in all_panels(themed["panels"]) if p.get("type") == PLUGIN)
    print(f"wrote {out} ({out.stat().st_size:,} B): {len(list(all_panels(themed['panels'])))} panels, "
          f"{html_panels} retro HTML panels, every query and info note kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
