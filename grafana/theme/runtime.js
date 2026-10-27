// retro-neon-ui for Grafana: page runtime. apply_theme.py prepends this to the onRender code of ONE HTML Graphics
// panel (the theme carrier). It runs on every data refresh, so it is idempotent:
// - adds one <style id="rt-grafana-theme"> (replaced only when the build VERSION changes) and one CRT overlay;
// - sets body.rt-grafana ONLY while the URL is one of the themed dashboards (Grafana is a single-page app, so a
//   700 ms check switches the theme off as soon as you navigate elsewhere);
// - keeps body.rt-fx-off in sync with the CRT FX switch (localStorage "rt-fx");
// - plays the attract-mode intro at most every 12 h (never with reduced motion or FX off; ?rt-intro forces it).
// Placeholders (__RT_*__) are filled by apply_theme.py.
(() => {
  const VERSION = __RT_VERSION__;
  const DASH_UIDS = __RT_DASH_UIDS__;
  const INTRO = __RT_INTRO__; // null, or { title, tag, logo }
  const W = window;
  const state = W.__rtGrafana || (W.__rtGrafana = {});
  const esc = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Exact uid match, kept in shared state so the single timer always uses the dashboard that rendered last.
  // Not anchored to the start: a Grafana served under a sub-path has /grafana/d/<uid>/... paths.
  state.pathRe = new RegExp('/d/(' + DASH_UIDS.map(esc).join('|') + ')(/|$)');

  let style = document.getElementById('rt-grafana-theme');
  if (!style) {
    style = document.createElement('style');
    style.id = 'rt-grafana-theme';
    document.head.appendChild(style);
  }
  if (style.dataset.version !== VERSION) {
    style.textContent = __RT_GLOBAL_CSS__;
    style.dataset.version = VERSION;
  }
  if (!document.querySelector('body > .rt-crt')) {
    const crt = document.createElement('div');
    crt.className = 'rt-crt';
    crt.setAttribute('aria-hidden', 'true');
    crt.innerHTML = '<span class="rt-crt__roll"></span>';
    document.body.appendChild(crt);
  }

  // state.fxOff (set by the FX switch) wins over storage, so the switch still works when storage writes fail.
  state.sync = () => {
    document.body.classList.toggle('rt-grafana', state.pathRe.test(W.location.pathname));
    let off = false;
    if (typeof state.fxOff === 'boolean') off = state.fxOff;
    else { try { off = W.localStorage.getItem('rt-fx') === 'off'; } catch (e) { off = false; } }
    document.body.classList.toggle('rt-fx-off', off);
  };
  state.sync();
  if (!state.timer) state.timer = W.setInterval(() => state.sync(), 700);

  // Only on the themed dashboard itself: not in single-panel embeds (/d-solo/) or other routes.
  if (!INTRO || !state.pathRe.test(W.location.pathname)) return;
  const reduced = W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let store = null;
  try { W.localStorage.setItem('__rt', '1'); W.localStorage.removeItem('__rt'); store = W.localStorage; } catch (e) { store = null; }
  const last = store ? Number(store.getItem('rt-intro-grafana')) || 0 : 0;
  const since = Date.now() - last;
  const due = since < 0 || since > 12 * 3600 * 1000 || /[?&]rt-intro(=|&|$)/.test(W.location.search);
  if (state.introDone || !store || reduced || document.body.classList.contains('rt-fx-off') || !due) return;
  state.introDone = true;
  store.setItem('rt-intro-grafana', String(Date.now()));

  const intro = document.createElement('div');
  intro.className = 'rt-intro';
  intro.setAttribute('aria-hidden', 'true');
  intro.innerHTML = '<div class="rt-intro__screen"><div class="rt-imark"><span class="rt-imark__stripes">' +
    '<i></i><i></i><i></i><i></i><i></i><i></i><i></i></span><span class="rt-imark__ring"><svg viewBox="0 0 100 100">' +
    '<circle cx="50" cy="50" r="46"></circle></svg></span><span class="rt-imark__word"><span class="rt-imark__name">' +
    '</span><span class="rt-imark__tag"></span></span></div><p class="rt-intro__skip">PRESS ANY KEY</p></div>';
  intro.querySelector('.rt-imark__name').textContent = INTRO.title || '';
  if (INTRO.logo) {
    const img = document.createElement('img');
    img.alt = '';
    img.src = INTRO.logo;
    intro.querySelector('.rt-imark__ring').appendChild(img);
  } else {
    const glyph = document.createElement('span'); // no logo: the title's first letter in the ring
    glyph.className = 'rt-imark__glyph';
    glyph.textContent = String(INTRO.title || '?').charAt(0).toUpperCase();
    intro.querySelector('.rt-imark__ring').appendChild(glyph);
  }
  document.body.appendChild(intro);

  // The tagline decodes once the ring and name are up.
  const tag = intro.querySelector('.rt-imark__tag');
  const final = String(INTRO.tag || '').toUpperCase();
  const glyphs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+=?';
  let frame = 0;
  let scramble = null;
  const startScramble = W.setTimeout(() => {
    scramble = W.setInterval(() => {
      frame += 1;
      const settled = Math.floor(final.length * frame / 16);
      tag.textContent = [...final].map((ch, i) => (i < settled || ch === ' ' ? ch : glyphs[Math.floor(Math.random() * glyphs.length)])).join('');
      if (frame >= 16) { W.clearInterval(scramble); tag.textContent = final; }
    }, 34);
  }, 1250);
  let finished = false;
  const finish = () => {
    if (finished) return;
    finished = true;
    document.removeEventListener('keydown', finish, true);
    intro.classList.add('is-out');
    W.setTimeout(() => { W.clearTimeout(startScramble); W.clearInterval(scramble); intro.remove(); }, 700);
  };
  intro.addEventListener('click', finish);
  document.addEventListener('keydown', finish, true);
  W.setTimeout(finish, 2900);
})();
