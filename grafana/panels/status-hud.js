// status-hud: header (mark, title, one status line, chips, CRT FX switch) + LED meters, driven by CFG.
// CFG (filled by apply_theme.py from the panel's config):
//   meters: [{ label, value: "A" | { ratio: ["B", "C"], scale: 100 }, format, warn, crit,
//              bar: { max: 100 } | { maxRef: "K" }, hint, status, warnText, critText }]
//   chips:  ["{F:int} CORES", "UPTIME {E:duration}"]       okText, noDataText
// Text templates take {REF:format} (a query's last value) and {value:format} (the meter's own value).
// Formats: percent, number, number2, int, bytes, duration. Values are looked up by refId, never by series order.
const CFG = __RT_PANEL_CONFIG__;
const $ = (id) => htmlNode.getElementById(id);
const lastOf = (refId) => {
  const frame = ((data && data.series) || []).find((f) => f.refId === refId);
  const field = frame && (frame.fields || []).find((f) => f.type === 'number');
  if (!field) return null;
  const values = field.values && field.values.buffer ? field.values.buffer : field.values;
  const n = values ? values.length : 0;
  if (!n) return null;
  const raw = typeof values.get === 'function' ? values.get(n - 1) : values[n - 1];
  if (raw === null || raw === undefined) return null; // a gap is "no data", never a real zero
  const v = Number(raw);
  return Number.isFinite(v) ? v : null;
};
const fin = (v) => typeof v === 'number' && Number.isFinite(v);
const FORMATS = {
  percent: (v) => v.toFixed(1) + '%',
  number: (v) => (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1)),
  number2: (v) => v.toFixed(2),
  int: (v) => String(Math.round(v)),
  bytes: (v) => {
    const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];
    let size = v;
    let i = 0;
    while (Math.abs(size) >= 1024 && i < units.length - 1) { size /= 1024; i += 1; }
    return size.toFixed(Math.abs(size) >= 100 ? 0 : Math.abs(size) >= 10 ? 1 : 2) + ' ' + units[i];
  },
  duration: (s) => {
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    return d > 0 ? d + 'D ' + h + 'H' : h > 0 ? h + 'H ' + m + 'M' : m + 'M';
  },
};
const fmt = (v, kind) => (fin(v) ? (FORMATS[kind] || FORMATS.number)(v) : '--');
const tpl = (text, own) => String(text || '').replace(/\{([A-Za-z0-9_]+)(?::([a-z0-9]+))?\}/g, (_, ref, kind) =>
  fmt(ref === 'value' ? own : lastOf(ref), kind || 'number'));
const valueOf = (spec) => {
  if (typeof spec === 'string') return lastOf(spec);
  if (spec && Array.isArray(spec.ratio)) {
    const a = lastOf(spec.ratio[0]);
    const b = lastOf(spec.ratio[1]);
    return fin(a) && fin(b) && b !== 0 ? (a / b) * (spec.scale || 1) : null;
  }
  return null;
};
const setText = (id, text) => { const el = $(id); if (el) el.textContent = text; };
// Dashboard variables in the title ("$instance"): the plugin exposes Grafana's template service as getTemplateSrv.
const vars = (s) => {
  try { return typeof getTemplateSrv === 'function' ? getTemplateSrv().replace(String(s)) : String(s); } catch (e) { return String(s); }
};
const titleEl = htmlNode.querySelector('.hud__title');
if (titleEl && String(CFG.title || '').includes('$')) {
  const t = vars(CFG.title);
  if (titleEl.textContent !== t) { titleEl.textContent = t; titleEl.dataset.text = t; }
  const glyph = htmlNode.querySelector('.rt-mark__glyph');
  if (glyph) glyph.textContent = t.charAt(0).toUpperCase();
}

const crit = [];
const warn = [];
let anyData = false;
(CFG.meters || []).forEach((m, i) => {
  const v = valueOf(m.value);
  if (fin(v)) anyData = true;
  const level = !fin(v) ? '' : fin(m.crit) && v >= m.crit ? 'crit' : fin(m.warn) && v >= m.warn ? 'warn' : '';
  setText('v-' + i, fmt(v, m.format));
  if (m.hint) setText('h-' + i, tpl(m.hint, v));
  const max = m.bar && m.bar.maxRef ? lastOf(m.bar.maxRef) : (m.bar && m.bar.max) || 100;
  const fill = fin(v) && fin(max) && max > 0 ? (v / max) * 100 : null;
  const bar = $('b-' + i);
  if (bar) {
    if (bar.children.length !== 20) bar.innerHTML = '<i></i>'.repeat(20);
    const lit = fin(fill) ? Math.max(v > 0 ? 1 : 0, Math.min(20, Math.round(fill / 5))) : 0;
    [...bar.children].forEach((seg, j) => seg.classList.toggle('on', j < lit));
  }
  const card = $('m-' + i);
  if (card) { if (level) card.dataset.state = level; else delete card.dataset.state; }
  const name = m.status || String(m.label || '').toUpperCase();
  if (level === 'crit') crit.push(tpl(m.critText || name + ' CRITICAL', v));
  else if (level === 'warn') warn.push(tpl(m.warnText || name + ' HIGH', v));
});
(CFG.chips || []).forEach((chip, i) => setText('c-' + i, tpl(chip)));

const statusEl = $('hud-status');
if (statusEl) statusEl.dataset.level = !anyData ? 'warn' : crit.length ? 'crit' : warn.length ? 'warn' : 'ok';
setText('hud-status-text', !anyData ? '> ' + (CFG.noDataText || 'NO SIGNAL')
  : crit.length || warn.length ? '> ' + crit.concat(warn).join(' / ') : '> ' + (CFG.okText || 'ALL SYSTEMS NOMINAL'));
