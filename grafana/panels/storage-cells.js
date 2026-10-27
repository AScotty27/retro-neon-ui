// storage-cells: one power cell per filesystem. CFG: { usedRef: "A" (percent used per series),
// freeRef: "B" (bytes free per series, optional), label: "mountpoint" (series label to key on),
// order: ["/", "/data"] (optional; listed first, the rest follow sorted), names: { "/": "/ root" } (optional),
// warn: 75, crit: 90 }. Every series the query returns gets a cell, so new mounts show up on their own.
const CFG = __RT_PANEL_CONFIG__;
const host = htmlNode.getElementById('cells');
const lastNumber = (frame) => {
  const field = (frame.fields || []).find((f) => f.type === 'number');
  if (!field) return { value: null, labels: {} };
  const values = field.values && field.values.buffer ? field.values.buffer : field.values;
  const n = values ? values.length : 0;
  const raw = n ? (typeof values.get === 'function' ? values.get(n - 1) : values[n - 1]) : null;
  const v = raw === null || raw === undefined ? NaN : Number(raw); // a gap is "no data", never a real zero
  return { value: Number.isFinite(v) ? v : null, labels: field.labels || {} };
};
const bytes = (v) => {
  if (!Number.isFinite(v)) return '--';
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
  let size = v;
  let i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i += 1; }
  return size.toFixed(size >= 100 ? 0 : size >= 10 ? 1 : 2) + ' ' + units[i] + ' free';
};
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const key = CFG.label || 'mountpoint';
const used = {};
const free = {};
const seen = {};
for (const frame of (data && data.series) || []) {
  const { value, labels } = lastNumber(frame);
  // Without the label: the legend name, else the n-th series of each query (so used and free still pair up).
  seen[frame.refId] = (seen[frame.refId] || 0) + 1;
  const id = labels[key] || frame.name || '#' + seen[frame.refId];
  if (frame.refId === (CFG.usedRef || 'A')) used[id] = value;
  else if (frame.refId === CFG.freeRef) free[id] = value;
}
const order = CFG.order || [];
const ids = Object.keys(used).sort((a, b) => {
  const ia = order.indexOf(a);
  const ib = order.indexOf(b);
  if (ia !== -1 || ib !== -1) return (ia === -1 ? 1e9 : ia) - (ib === -1 ? 1e9 : ib);
  return a.localeCompare(b);
});
const warnAt = Number.isFinite(CFG.warn) ? CFG.warn : 75;
const critAt = Number.isFinite(CFG.crit) ? CFG.crit : 90;
const html = ids.length ? ids.map((id) => {
  const u = used[id];
  const ok = Number.isFinite(u);
  const lit = ok ? Math.max(u > 0 ? 1 : 0, Math.min(20, Math.round(u / 5))) : 0;
  const state = !ok ? '' : u >= critAt ? 'crit' : u >= warnAt ? 'warn' : '';
  const segs = Array.from({ length: 20 }, (_, i) => (i < lit ? '<i class="on"></i>' : '<i></i>')).join('');
  return '<article class="rt-box cell"' + (state ? ' data-state="' + state + '"' : '') + '>' +
    '<div class="rt-label">' + esc((CFG.names && CFG.names[id]) || id) + '</div>' +
    '<div class="cell__value">' + (ok ? u.toFixed(1) + '%' : '--') + '</div>' +
    '<div class="cell__bar">' + segs + '</div>' +
    '<div class="cell__meta">' + (CFG.freeRef ? bytes(free[id]) : '&nbsp;') + '</div></article>';
}).join('') : '<div class="cells__empty">&gt; No filesystem data</div>';
if (host && host.__rtHtml !== html) { host.innerHTML = html; host.__rtHtml = html; }
