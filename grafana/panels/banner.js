// banner: a slim title bar (mark, chrome title, kicker, CRT FX switch). It needs no data; its job is to carry the
// page runtime when a dashboard has no status-hud. A "$variable" in the title is filled from the dashboard.
const CFG = __RT_PANEL_CONFIG__;
const titleEl = htmlNode.querySelector('.banner__title');
if (titleEl && String(CFG.title || '').includes('$')) {
  let t = String(CFG.title);
  try { if (typeof getTemplateSrv === 'function') t = getTemplateSrv().replace(t); } catch (e) { /* keep the raw title */ }
  if (titleEl.textContent !== t) { titleEl.textContent = t; titleEl.dataset.text = t; }
  const glyph = htmlNode.querySelector('.rt-mark__glyph');
  if (glyph) glyph.textContent = t.charAt(0).toUpperCase();
}
