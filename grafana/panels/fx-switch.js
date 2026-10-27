// CRT FX switch for any retro panel that renders a button#rt-fx (status-hud, banner). Shares state with the page
// runtime: body.rt-fx-off, window.__rtGrafana.fxOff and localStorage "rt-fx".
(() => {
  const button = htmlNode.getElementById('rt-fx');
  const root = htmlNode.querySelector('.rt-panel');
  const sync = () => {
    const off = document.body.classList.contains('rt-fx-off');
    if (button) { button.setAttribute('aria-pressed', String(!off)); button.textContent = 'CRT FX ' + (off ? 'OFF' : 'ON'); }
    if (root) root.dataset.fx = off ? 'off' : 'on';
  };
  if (button && !button.dataset.bound) {
    button.dataset.bound = '1';
    button.addEventListener('click', () => {
      const off = !document.body.classList.contains('rt-fx-off');
      document.body.classList.toggle('rt-fx-off', off);
      if (window.__rtGrafana) window.__rtGrafana.fxOff = off;
      try { localStorage.setItem('rt-fx', off ? 'off' : 'on'); } catch (e) { /* storage blocked: this page only */ }
      sync();
    });
  }
  sync();
})();
