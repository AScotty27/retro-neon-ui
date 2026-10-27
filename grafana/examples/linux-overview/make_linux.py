"""Regenerate the Linux overview example: source.json (a plain node_exporter + cAdvisor dashboard) and retro.json.

    python grafana/examples/linux-overview/make_linux.py
    python grafana/tools/apply_theme.py grafana/examples/linux-overview/source.json \
        --config grafana/examples/linux-overview/retro.json -o grafana/examples/linux-overview/linux-overview-retro.json

Variables: $ds (Prometheus data source), $instance (node_exporter target), $cadvisor (cAdvisor target),
$mountpoint (filesystems, multi), $container (containers, multi). Nothing is hardcoded to one machine.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DS = {"type": "prometheus", "uid": "${ds}"}
NODE = 'instance="$instance"'
FS = NODE + ', mountpoint=~"$mountpoint", fstype!~"tmpfs|devtmpfs|squashfs|overlay|fuse.*|proc|sysfs|ramfs|nsfs"'
CAD = 'instance="$cadvisor", image!=""'
CORES = f'count(count by (cpu) (node_cpu_seconds_total{{mode="idle", {NODE}}}))'
KNOWN = f"max by (name) (max_over_time(container_last_seen{{{CAD}}}[1h]))"   # seen at any time in the last hour
LIVE = f"max by (name) ((time() - container_last_seen{{{CAD}}}) < 120)"       # seen in the last 120 s
LIVE_COUNT = f"count({LIVE})"
USED_PCT = (f"100 * (node_filesystem_size_bytes{{{FS}}} - node_filesystem_free_bytes{{{FS}}}) / "
            f"(node_filesystem_size_bytes{{{FS}}} - node_filesystem_free_bytes{{{FS}}} + node_filesystem_avail_bytes{{{FS}}})")


def q(ref, expr, legend=None):
    target = {"refId": ref, "datasource": DS, "expr": expr}
    if legend:
        target["legendFormat"] = legend
    return target


def timeseries(pid, title, pos, targets, unit="short", color="palette-classic", steps=None, desc="", minmax=None):
    custom = {"drawStyle": "line", "lineWidth": 1, "fillOpacity": 0}
    if steps:
        custom["thresholdsStyle"] = {"mode": "line"}
    defaults = {"unit": unit, "color": {"mode": color}, "custom": custom,
                "thresholds": {"mode": "absolute", "steps": steps or [{"color": "green", "value": None}]}}
    if minmax:
        defaults["min"], defaults["max"] = minmax
    return {"id": pid, "type": "timeseries", "title": title, "description": desc, "gridPos": pos, "datasource": DS,
            "targets": targets, "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                        "tooltip": {"mode": "multi"}}}


def bars(pid, title, pos, target, unit, steps, desc):
    return {"id": pid, "type": "bargauge", "title": title, "description": desc, "gridPos": pos, "datasource": DS,
            "targets": [target],
            "options": {"displayMode": "gradient", "orientation": "horizontal", "showUnfilled": True, "valueMode": "color",
                        "reduceOptions": {"calcs": ["lastNotNull"], "values": False}},
            "fieldConfig": {"defaults": {"unit": unit, "min": 0, "color": {"mode": "thresholds"},
                                         "thresholds": {"mode": "absolute", "steps": steps}}, "overrides": []}}


def variable(name, label, query, multi=False):
    return {"name": name, "label": label, "type": "query", "datasource": DS, "refresh": 2, "sort": 1,
            "query": {"query": query, "refId": name}, "definition": query, "multi": multi, "includeAll": multi,
            "current": {"selected": True, "text": "All", "value": "$__all"} if multi else {}}


def main():
    cpu_steps = [{"color": "green", "value": None}, {"color": "yellow", "value": 65}, {"color": "red", "value": 85}]
    panels = [
        {"id": 1, "type": "alertlist", "title": "Active alerts", "description": "Alert rules that are firing or pending.",
         "gridPos": {"x": 0, "y": 0, "w": 7, "h": 10},
         "options": {"viewMode": "list", "maxItems": 20, "sortOrder": 1, "dashboardAlerts": False, "showInstances": True,
                     "groupMode": "default", "alertName": "", "alertInstanceLabelFilter": "",
                     "stateFilter": {"firing": True, "pending": True, "error": True, "noData": True, "normal": False}}},
        timeseries(2, "CPU used over time", {"x": 7, "y": 0, "w": 17, "h": 10},
                   [q("A", f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle", {NODE}}}[1m])) * 100)', "CPU")],
                   "percent", "continuous-GrYlRd", cpu_steps, "Average CPU busy across all cores.", (0, 100)),
        timeseries(3, "Memory breakdown", {"x": 0, "y": 10, "w": 8, "h": 9},
                   [q("A", f"node_memory_MemTotal_bytes{{{NODE}}} - node_memory_MemAvailable_bytes{{{NODE}}}", "Used"),
                    q("B", f"node_memory_Cached_bytes{{{NODE}}}", "Cache"),
                    q("C", f"node_memory_Buffers_bytes{{{NODE}}}", "Buffers")],
                   "bytes", desc="Used is MemTotal minus MemAvailable (cache-aware)."),
        timeseries(4, "Temperatures", {"x": 8, "y": 10, "w": 8, "h": 9},
                   [q("A", f"max by (chip) (node_hwmon_temp_celsius{{{NODE}}})", "{{chip}}")],
                   "celsius", desc="Hottest sensor per hardware monitor chip."),
        timeseries(5, "Disk busy by device", {"x": 16, "y": 10, "w": 8, "h": 9},
                   [q("A", f'100 * rate(node_disk_io_time_seconds_total{{{NODE}, device!~"loop.*|ram.*|dm-.*|zram.*"}}[5m])',
                      "{{device}}")], "percent", desc="Share of time each disk was busy.", minmax=(0, 100)),
        timeseries(6, "Network out by container", {"x": 0, "y": 19, "w": 12, "h": 9},
                   [q("A", f'sum by (name) (rate(container_network_transmit_bytes_total{{{CAD}, name=~"$container"}}[5m])) * 8',
                      "{{name}}")], "bps", desc="cAdvisor transmit rate per container."),
        timeseries(7, "Network in by container", {"x": 12, "y": 19, "w": 12, "h": 9},
                   [q("A", f'sum by (name) (rate(container_network_receive_bytes_total{{{CAD}, name=~"$container"}}[5m])) * 8',
                      "{{name}}")], "bps", desc="cAdvisor receive rate per container."),
        timeseries(8, "Filesystem usage over time", {"x": 0, "y": 28, "w": 24, "h": 8},
                   [q("A", USED_PCT, "{{mountpoint}}")], "percent", desc="Percent used per mount, root-reserved aware.",
                   minmax=(0, 100)),
        bars(9, "Top containers by memory", {"x": 0, "y": 36, "w": 12, "h": 9},
             q("A", f'topk(8, container_memory_working_set_bytes{{{CAD}, name=~"$container"}})', "{{name}}"), "bytes",
             [{"color": "green", "value": None}, {"color": "yellow", "value": 2 ** 33}, {"color": "red", "value": 2 ** 35}],
             "Working set memory per container."),
        bars(10, "Top containers by CPU share", {"x": 12, "y": 36, "w": 12, "h": 9},
             q("A", f'topk(8, 100 * sum by (name) (rate(container_cpu_usage_seconds_total{{{CAD}, name=~"$container"}}[5m])) / '
                    f"scalar({CORES}))", "{{name}}"), "percent",
             [{"color": "green", "value": None}, {"color": "yellow", "value": 25}, {"color": "red", "value": 60}],
             "Share of all cores per container."),
        {"id": 11, "type": "state-timeline", "title": "Container status history",
         "description": "Live when cAdvisor saw the container in the last 120 s; down when it was seen in the last hour but not now.",
         "gridPos": {"x": 0, "y": 45, "w": 24, "h": 14}, "datasource": DS,
         "targets": [q("A", f'(max by (name) ((time() - container_last_seen{{{CAD}, name=~"$container"}}) < bool 120)) or '
                            f'(max by (name) (max_over_time(container_last_seen{{{CAD}, name=~"$container"}}[1h])) * 0)', "{{name}}")],
         "options": {"mergeValues": True, "showValue": "auto", "rowHeight": 0.9,
                     "legend": {"showLegend": False, "displayMode": "list", "placement": "bottom"}},
         "fieldConfig": {"defaults": {"color": {"mode": "thresholds"}, "custom": {"fillOpacity": 70, "lineWidth": 0},
                                      "mappings": [{"type": "value", "options": {"0": {"color": "red", "text": "Down"},
                                                                                  "1": {"color": "green", "text": "Up"}}}],
                                      "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None},
                                                                                    {"color": "green", "value": 1}]}},
                         "overrides": []}},
    ]
    dashboard = {
        "uid": "linux-overview-retro", "title": "Linux Server Overview", "tags": ["linux", "node_exporter", "cadvisor"],
        "timezone": "browser", "schemaVersion": 41, "refresh": "15s", "time": {"from": "now-3h", "to": "now"},
        "graphTooltip": 1, "editable": True, "annotations": {"list": []}, "panels": panels,
        "description": "Host and container overview for node_exporter + cAdvisor.",
        "templating": {"list": [
            {"name": "ds", "label": "Data source", "type": "datasource", "query": "prometheus", "current": {}},
            variable("instance", "Host", "label_values(node_uname_info, instance)"),
            variable("cadvisor", "cAdvisor", "label_values(container_last_seen, instance)"),
            variable("mountpoint", "Mounts", f'label_values(node_filesystem_size_bytes{{{NODE}, fstype!~"tmpfs|devtmpfs|squashfs|overlay"}}, mountpoint)', True),
            variable("container", "Containers", 'label_values(container_last_seen{instance="$cadvisor", image!=""}, name)', True),
        ]},
    }
    config = {
        "intro": {"title": "LINUX OVERVIEW", "tag": "Server status"},
        "add": [
            {"kind": "status-hud", "height": 11, "description": "Host summary: the worst problem is named first.",
             "targets": [
                 q("A", f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle", {NODE}}}[5m])) * 100)'),
                 q("B", f"node_memory_MemTotal_bytes{{{NODE}}} - node_memory_MemAvailable_bytes{{{NODE}}}"),
                 q("C", f"node_memory_MemTotal_bytes{{{NODE}}}"),
                 q("D", f"node_load5{{{NODE}}} / scalar({CORES})"),
                 q("E", f"time() - node_boot_time_seconds{{{NODE}}}"),
                 q("F", CORES),
                 q("G", f"max({USED_PCT})"),
                 q("H", f'max(100 * rate(node_disk_io_time_seconds_total{{{NODE}, device!~"loop.*|ram.*|dm-.*|zram.*"}}[5m]))'),
                 # Down = seen in the last hour but not now. A stopped container's series goes stale at once, so
                 # "last seen > 120 s ago" alone would never fire; max_over_time remembers it for an hour.
                 q("I", f"count({KNOWN}) - ({LIVE_COUNT} or vector(0))"),
                 q("J", LIVE_COUNT),
                 q("K", f"count({KNOWN})"),
             ],
             "config": {
                 "title": "$instance", "kicker": "Linux server overview",
                 "meters": [
                     {"label": "CPU used", "value": "A", "format": "percent", "warn": 65, "crit": 85, "hint": "Last 5 minutes"},
                     {"label": "RAM used", "value": {"ratio": ["B", "C"], "scale": 100}, "format": "percent", "warn": 75,
                      "crit": 90, "hint": "{B:bytes} of {C:bytes}"},
                     {"label": "Load / core", "value": "D", "format": "number2", "warn": 0.7, "crit": 1, "bar": {"max": 1},
                      "hint": "5 min, 1.00 = full"},
                     {"label": "Max FS used", "value": "G", "format": "percent", "warn": 75, "crit": 90, "hint": "Worst mount"},
                     {"label": "Busiest disk", "value": "H", "format": "percent", "warn": 50, "crit": 80, "hint": "5 minute peak"},
                     {"label": "Containers down", "value": "I", "format": "int", "warn": 1, "crit": 1, "bar": {"maxRef": "K"},
                      "hint": "{J:int}/{K:int} reporting", "critText": "{value:int} CONTAINER(S) DOWN"},
                 ],
                 "chips": ["{F:int} CORES", "UPTIME {E:duration}", "{J:int} / {K:int} LIVE"],
             }},
            {"kind": "storage-cells", "height": 7, "description": "Percent used and free space per mount.",
             "targets": [q("A", USED_PCT), q("B", f"node_filesystem_avail_bytes{{{FS}}}")],
             "config": {"title": "Filesystems", "subtitle": "used + free space", "usedRef": "A", "freeRef": "B",
                        "label": "mountpoint", "order": ["/"]}},
            {"kind": "service-grid", "height": 10,
             "description": "Every container cAdvisor saw in the last hour; down = not seen for 120 s.",
             "targets": [q("A", f"({LIVE} * 0) or ({KNOWN} * 0 + 1)")],
             "config": {"title": "Container health", "refId": "A", "label": "name", "downWhen": "nonzero"}},
        ],
        "seriesColors": {"3": {"Used": "#ff2e9a", "Cache": "#2de2ff", "Buffers": "#4d5bff"}},
    }
    for name, doc in (("source.json", dashboard), ("retro.json", config)):
        (HERE / name).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote", HERE / "source.json", "and", HERE / "retro.json")


if __name__ == "__main__":
    main()
