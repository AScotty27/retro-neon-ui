"""Regenerate the TestData demo: source.json (a plain dashboard) and retro.json (its retro config).

    python grafana/examples/testdata-demo/make_demo.py
    python grafana/tools/apply_theme.py grafana/examples/testdata-demo/source.json \
        --config grafana/examples/testdata-demo/retro.json -o grafana/examples/testdata-demo/retro-neon-demo.json

Uses only Grafana's built-in TestData data source (uid "rt-testdata"), so it renders on any Grafana with no real
metrics. One service is down on purpose, to show the alarm states.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DS = {"type": "grafana-testdata-datasource", "uid": "rt-testdata"}


def csv(ref, values, alias):
    return {"refId": ref, "datasource": DS, "scenarioId": "csv_metric_values",
            "stringInput": ",".join(str(v) for v in values), "alias": alias}


def walk(ref, alias=None, series=1, lo=0.0, hi=100.0):
    target = {"refId": ref, "datasource": DS, "scenarioId": "random_walk", "seriesCount": series,
              "min": lo, "max": hi, "startValue": lo + (hi - lo) / 3}
    if alias:
        target["alias"] = alias
    return target


def raw(ref, label, rows):
    """One frame per labelled value, the shape a Prometheus instant query returns."""
    frames = [{"schema": {"refId": ref, "fields": [{"name": "Value", "type": "number", "labels": {label: name}}]},
               "data": {"values": [[value]]}} for name, value in rows]
    return {"refId": ref, "datasource": DS, "scenarioId": "raw_frame", "rawFrameContent": json.dumps(frames)}


def timeseries(pid, title, pos, targets, unit="short", color="palette-classic", thresholds=None, desc=""):
    custom = {"drawStyle": "line", "lineWidth": 1, "fillOpacity": 0}
    if thresholds:
        custom["thresholdsStyle"] = {"mode": "line"}
    return {
        "id": pid, "type": "timeseries", "title": title, "description": desc, "gridPos": pos, "datasource": DS,
        "targets": targets,
        "fieldConfig": {"defaults": {"unit": unit, "color": {"mode": color}, "custom": custom,
                                     "thresholds": thresholds or {"mode": "absolute", "steps": [{"color": "green", "value": None}]}},
                        "overrides": []},
        "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True}, "tooltip": {"mode": "multi"}},
    }


def main():
    cpu_steps = {"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "yellow", "value": 65},
                                               {"color": "red", "value": 85}]}
    panels = [
        {"id": 1, "type": "alertlist", "title": "Active alerts", "description": "Alert rules that are firing or pending.",
         "gridPos": {"x": 0, "y": 0, "w": 7, "h": 9},
         "options": {"viewMode": "list", "maxItems": 10, "sortOrder": 1, "dashboardAlerts": False, "showInstances": True,
                     "groupMode": "default", "alertName": "", "alertInstanceLabelFilter": "",
                     "stateFilter": {"firing": True, "pending": True, "error": True, "noData": True, "normal": False}}},
        timeseries(2, "CPU used over time", {"x": 7, "y": 0, "w": 17, "h": 9}, [walk("A", "cpu")], "percent",
                   "continuous-GrYlRd", cpu_steps, "Average CPU busy across all cores. The line colour is the load level."),
        timeseries(3, "Memory breakdown", {"x": 0, "y": 9, "w": 12, "h": 9},
                   [walk("A", "Used", 1, 8e9, 20e9), walk("B", "Cache", 1, 20e9, 30e9), walk("C", "Buffers", 1, 1e9, 2e9)],
                   "bytes", desc="Used, cache and buffers."),
        timeseries(4, "Network by service", {"x": 12, "y": 9, "w": 12, "h": 9}, [walk("A", None, 4, 0, 5e6)], "bps",
                   desc="Traffic per service."),
        {"id": 5, "type": "bargauge", "title": "Top services by memory", "description": "Working set per service.",
         "gridPos": {"x": 0, "y": 18, "w": 12, "h": 9}, "datasource": DS, "targets": [walk("A", None, 6, 1e8, 2e9)],
         "options": {"displayMode": "gradient", "orientation": "horizontal", "showUnfilled": True, "valueMode": "color",
                     "reduceOptions": {"calcs": ["lastNotNull"], "values": False}},
         "fieldConfig": {"defaults": {"unit": "bytes", "min": 0, "max": 2.5e9, "color": {"mode": "thresholds"},
                                      "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None},
                                                     {"color": "yellow", "value": 1e9}, {"color": "red", "value": 2e9}]}},
                         "overrides": []}},
        {"id": 6, "type": "state-timeline", "title": "Service status history", "description": "1 = up, 0 = down.",
         "gridPos": {"x": 12, "y": 18, "w": 12, "h": 9}, "datasource": DS,
         "targets": [csv("A", [1] * 8, "api"), csv("B", [1, 1, 1, 0, 0, 1, 1, 1], "worker"), csv("C", [1] * 8, "web"),
                     csv("D", [1, 1, 1, 1, 1, 1, 0, 0], "queue")],
         "options": {"mergeValues": True, "showValue": "auto", "rowHeight": 0.9,
                     "legend": {"showLegend": True, "displayMode": "list", "placement": "bottom"}},
         "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "custom": {"fillOpacity": 70, "lineWidth": 0},
                                      "mappings": [{"type": "value", "options": {"0": {"color": "red", "text": "Down"},
                                                                                  "1": {"color": "green", "text": "Up"}}}],
                                      "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None},
                                                                                    {"color": "green", "value": 1}]}},
                         "overrides": []}},
    ]
    dashboard = {
        "uid": "retro-neon-demo", "title": "Retro Neon Demo", "tags": ["retro-neon-ui", "demo"], "timezone": "browser",
        "schemaVersion": 41, "refresh": "", "time": {"from": "now-3h", "to": "now"}, "graphTooltip": 1, "editable": True,
        "templating": {"list": []}, "annotations": {"list": []}, "panels": panels,
        "description": "Demo dashboard on the built-in TestData data source (no real metrics).",
    }
    config = {
        "intro": {"title": "NEON OPS", "tag": "System overview"},
        "add": [
            {"kind": "status-hud", "height": 11, "description": "Host summary: the worst problem is named first.",
             "targets": [csv("A", [12, 18, 31, 24, 27], "cpu"), csv("B", [17.2e9, 17.4e9], "ram used"),
                         csv("C", [64e9, 64e9], "ram total"), csv("D", [0.31, 0.42], "load per core"),
                         csv("E", [1310000, 1310100], "uptime"), csv("F", [16, 16], "cores"), csv("G", [61, 61.3], "max fs"),
                         csv("H", [4.2, 7.9], "disk busy"), csv("I", [1, 1], "down"), csv("J", [11, 11], "live"),
                         csv("K", [12, 12], "total")],
             "config": {
                 "title": "Neon Ops", "kicker": "System overview",
                 "meters": [
                     {"label": "CPU used", "value": "A", "format": "percent", "warn": 65, "crit": 85, "hint": "Last 5 minutes"},
                     {"label": "RAM used", "value": {"ratio": ["B", "C"], "scale": 100}, "format": "percent", "warn": 75,
                      "crit": 90, "hint": "{B:bytes} of {C:bytes}"},
                     {"label": "Load / core", "value": "D", "format": "number2", "warn": 0.7, "crit": 1, "bar": {"max": 1},
                      "hint": "5 min, 1.00 = full"},
                     {"label": "Max FS used", "value": "G", "format": "percent", "warn": 75, "crit": 90, "hint": "Worst mount"},
                     {"label": "Busiest disk", "value": "H", "format": "percent", "warn": 50, "crit": 80, "hint": "5 minute peak"},
                     {"label": "Services down", "value": "I", "format": "int", "warn": 1, "crit": 1, "bar": {"maxRef": "K"},
                      "hint": "{J:int}/{K:int} reporting", "critText": "{value:int} SERVICE(S) DOWN"},
                 ],
                 "chips": ["{F:int} CORES", "UPTIME {E:duration}", "{J:int} / {K:int} LIVE"],
             }},
            {"kind": "storage-cells", "height": 7, "description": "Percent used and free space per mount.",
             "targets": [raw("A", "mountpoint", [("/", 41.2), ("/var", 61.3), ("/srv", 22.8), ("/backup", 77.4)]),
                         raw("B", "mountpoint", [("/", 58e9), ("/var", 210e9), ("/srv", 1.4e12), ("/backup", 0.9e12)])],
             "config": {"title": "Filesystems", "subtitle": "used + free space", "usedRef": "A", "freeRef": "B",
                        "label": "mountpoint", "order": ["/"]}},
            {"kind": "service-grid", "height": 6, "description": "Every scrape target: up or down.",
             "targets": [raw("A", "job", [("api", 1), ("web", 1), ("worker", 0), ("queue", 1), ("cache", 1), ("db", 1),
                                          ("auth", 1), ("search", 1), ("mailer", 1), ("scheduler", 1), ("metrics", 1),
                                          ("gateway", 1)])],
             "config": {"title": "Service health", "refId": "A", "label": "job", "downWhen": "zero"}},
        ],
        "seriesColors": {"3": {"Used": "#ff2e9a", "Cache": "#2de2ff", "Buffers": "#4d5bff"}},
    }
    for name, doc in (("source.json", dashboard), ("retro.json", config)):
        (HERE / name).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", HERE / "source.json", "and", HERE / "retro.json")


if __name__ == "__main__":
    main()
