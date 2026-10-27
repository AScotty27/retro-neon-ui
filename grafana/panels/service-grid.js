// service-grid: one lit tile per series (service, target, container). CFG: { refId: "A", label: "job" (series label
// that names the tile), downWhen: "zero" (Prometheus `up`: 0 = down) | "nonzero" (e.g. "last seen > 120 s" as a
// 0/1 bool: 1 = down), noun: "ONLINE" }. Down first (red, blinking), data gaps grey "?", then the rest A to Z.
const CFG = __RT_PANEL_CONFIG__;
const tilesEl = htmlNode.getElementById('grid-tiles');
const sumEl = htmlNode.getElementById('grid-sum');
const rows = [];
for (const frame of (data && data.series) || []) {
  if (CFG.refId && frame.refId !== CFG.refId) continue;
  const field = (frame.fields || []).find((f) => f.type === 'number');
  if (!field) continue;
  const values = field.values && field.values.buffer ? field.values.buffer : field.values;
  const n = values ? values.length : 0;
  const raw = n ? (typeof values.get === 'function' ? values.get(n - 1) : values[n - 1]) : null;
  const labels = field.labels || {};
  const name = labels[CFG.label || 'job'] || labels.instance || frame.name || '?';
  const v = raw === null || raw === undefined ? NaN : Number(raw);
  const down = CFG.downWhen === 'nonzero' ? v !== 0 : v === 0;
  rows.push({ name, state: !Number.isFinite(v) ? 'unknown' : down ? 'down' : 'up' });
}
const rank = { down: 0, unknown: 1, up: 2 };
rows.sort((a, b) => (a.state === b.state ? a.name.localeCompare(b.name) : rank[a.state] - rank[b.state]));
const downCount = rows.filter((r) => r.state === 'down').length;
const upCount = rows.filter((r) => r.state === 'up').length;
if (sumEl) {
  sumEl.textContent = rows.length ? upCount + ' / ' + rows.length + ' ' + (CFG.noun || 'ONLINE') + (downCount ? '  ' + downCount + ' DOWN' : '') : 'NO SIGNAL';
  sumEl.dataset.level = downCount ? 'crit' : 'ok';
}
if (tilesEl) {
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const html = rows.length ? rows.map((r) =>
    '<div class="tile" data-state="' + r.state + '" title="' + esc(r.name) + ': ' + (r.state === 'up' ? 'live' : r.state.toUpperCase()) + '">' +
    '<span class="tile__led" aria-hidden="true"></span><span class="tile__name">' + esc(r.name) + '</span>' +
    (r.state === 'down' ? '<span class="tile__state">DOWN</span>' : r.state === 'unknown' ? '<span class="tile__state">?</span>' : '') +
    '</div>').join('') : '<div class="grid__empty">&gt; No data</div>';
  if (tilesEl.__rtHtml !== html) { tilesEl.innerHTML = html; tilesEl.__rtHtml = html; }
}
