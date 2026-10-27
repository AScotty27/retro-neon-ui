/* retro-neon-ui runtime: attract-mode intro, CRT overlay, RGB-split glitch, nav text scramble, TV power-off page
   transitions, reveal on scroll and the CRT FX switch. Plain ES5, no dependencies. MIT license.
   For multi-page sites and server-rendered apps. Single-page apps (React and friends) use react/RetroNeon.tsx instead.
   Load it in <head> WITHOUT defer: the top half must run before first paint so the intro can hide the page.
   Config lives on <html>:
     data-rt-intro-title="Name"          turns the intro on, at most every 12 hours per browser (omit for no intro)
     data-rt-intro-tag="Tagline"         small line under the name
     data-rt-intro-logo="/logo.png"      image inside the neon ring
     data-rt-intro-logo-fit="contain"    for transparent cut-out logos (shown whole, not cropped round)
     data-rt-fx-target=".selector"       where the CRT FX switch goes; "float" = fixed bottom right; "none" = no switch
                                         (default: [data-rt-fx-slot], else the footer)
     data-rt-transitions="off"           no TV power-off on link clicks (for pages a client-side router owns)
   Script API: window.RetroNeon.fxOn() and window.RetroNeon.setFx(true|false), for an app's own settings menu. */
(function () {
  "use strict";

  var root = document.documentElement;
  var FX_KEY = "rt-fx";
  var INTRO_KEY = "rt-intro-seen";
  var GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+=?";
  var GLITCH_SELECTOR = ".brand strong, .rt-brand strong, .hero-title, .rt-hero-title, .page-header h1, " +
    ".rt-page-header h1, [data-rt-glitch]";
  var FX_HOSTS = ["[data-rt-fx-slot]", ".footer-layout", ".site-footer .container", ".rt-footer", "footer"];

  function storage(area) {
    try {
      var store = window[area];
      store.setItem("__rt", "1");
      store.removeItem("__rt");
      return store;
    } catch (error) {
      return null;
    }
  }

  var local = storage("localStorage");
  var session = storage("sessionStorage");
  var reduced = Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var fxOff = Boolean(local && local.getItem(FX_KEY) === "off");
  var introTitle = root.getAttribute("data-rt-intro-title");
  // The intro replays at most every 12 hours per browser (sessionStorage alone would replay it in every new tab).
  // With no storage at all it could not be remembered and would play on every page, so it is skipped instead.
  // ?rt-intro in the address forces it, for showing it off.
  var INTRO_GAP_MS = 12 * 60 * 60 * 1000;
  var introStore = local || session;
  var lastIntro = introStore ? Number(introStore.getItem(INTRO_KEY)) || 0 : 0;
  var forceIntro = /[?&]rt-intro(=|&|$)/.test(window.location.search);
  var sinceIntro = Date.now() - lastIntro;
  // A stamp from the future (clock moved back) counts as stale rather than blocking the intro indefinitely.
  var playIntro = Boolean(introTitle) && !reduced && !fxOff && Boolean(introStore) &&
    (forceIntro || sinceIntro < 0 || sinceIntro > INTRO_GAP_MS);

  root.classList.add("rt");
  root.classList.toggle("rt-fx-off", fxOff);
  if (reduced) {
    root.classList.add("rt-reduced");
  }
  if (playIntro) {
    root.classList.add("rt-intro-pending");
  } else if (!reduced && !fxOff) {
    root.classList.add("rt-power-on");
  }

  function motionOn() {
    return !reduced && !root.classList.contains("rt-fx-off");
  }

  // Every FX switch on the page re-reads the state through these.
  var fxListeners = [];

  function setFx(on) {
    root.classList.toggle("rt-fx-off", !on);
    if (local) {
      try {
        local.setItem(FX_KEY, on ? "on" : "off");
      } catch (error) {
        // Quota or privacy mode: the switch still works for this page.
      }
    }
    fxListeners.forEach(function (listener) {
      listener();
    });
  }

  window.RetroNeon = {
    fxOn: function () {
      return !root.classList.contains("rt-fx-off");
    },
    setFx: function (on) {
      setFx(Boolean(on));
    }
  };

  function scrambleTo(node, finalText, frames) {
    var frame = 0;
    var timer = window.setInterval(function () {
      frame += 1;
      var settled = Math.floor(finalText.length * frame / frames);
      var out = "";
      for (var i = 0; i < finalText.length; i += 1) {
        var ch = finalText.charAt(i);
        out += i < settled || ch === " " ? ch : GLYPHS.charAt(Math.floor(Math.random() * GLYPHS.length));
      }
      node.textContent = out;
      if (frame >= frames) {
        window.clearInterval(timer);
        node.textContent = finalText;
        node.removeAttribute("data-rt-scrambling");
      }
    }, 32);
    node.setAttribute("data-rt-scrambling", "");
  }

  function mountCrt() {
    var crt = document.createElement("div");
    crt.className = "rt-crt";
    crt.setAttribute("aria-hidden", "true");
    crt.innerHTML = '<span class="rt-crt__roll"></span>';
    document.body.appendChild(crt);
  }

  // Only plain-text headings: the glitch copies repeat textContent, so markup inside would be lost.
  function setupGlitch() {
    document.querySelectorAll(GLITCH_SELECTOR).forEach(function (node) {
      if (node.children.length) {
        return;
      }
      node.classList.add("rt-glitch");
      node.setAttribute("data-text", node.textContent.trim());
    });
  }

  // Mouse hover only, so keyboard and screen-reader users never meet half-scrambled text.
  function setupNavScramble() {
    document.querySelectorAll(".nav > a, .rt-nav > a").forEach(function (link) {
      link.addEventListener("mouseenter", function () {
        if (!motionOn() || link.children.length || link.hasAttribute("data-rt-scrambling")) {
          return;
        }
        scrambleTo(link, link.textContent, 9);
      });
    });
  }

  function findFxHost(target) {
    if (target) {
      return document.querySelector(target);
    }
    // In order of preference, not document order (a <footer> comes before the .footer-layout inside it).
    for (var i = 0; i < FX_HOSTS.length; i += 1) {
      var host = document.querySelector(FX_HOSTS[i]);
      if (host) {
        return host;
      }
    }
    return null;
  }

  function setupFxToggle() {
    var target = root.getAttribute("data-rt-fx-target");
    if (target === "none") {
      return;
    }
    var floating = target === "float";
    var host = floating ? document.body : findFxHost(target);
    if (!host) {
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.className = "rt-fx-toggle" + (floating ? " rt-fx-toggle--float" : "");

    function sync() {
      var on = !root.classList.contains("rt-fx-off");
      button.setAttribute("aria-pressed", String(on));
      button.textContent = "CRT FX " + (on ? "ON" : "OFF");
    }

    button.addEventListener("click", function () {
      setFx(root.classList.contains("rt-fx-off"));
    });

    fxListeners.push(sync);
    sync();
    if (floating) {
      host.appendChild(button);
    } else {
      host.insertBefore(button, host.firstChild);
    }
  }

  // TV power-off before same-site page loads. Files, API calls, new tabs and modified clicks are left alone.
  function setupTransitions() {
    if (root.getAttribute("data-rt-transitions") === "off") {
      return;
    }
    document.addEventListener("click", function (event) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      if (!motionOn() || !event.target.closest) {
        return;
      }

      var link = event.target.closest("a[href]");
      if (!link || link.hasAttribute("download") || (link.target && link.target !== "_self") || link.closest("[data-rt-no-transition]")) {
        return;
      }

      var url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || !/(\/|\.html?)$/.test(url.pathname) || /^\/(api|downloads)\//.test(url.pathname)) {
        return;
      }
      if (url.pathname === window.location.pathname && url.search === window.location.search) {
        return;
      }

      event.preventDefault();
      root.style.setProperty("--rt-origin-y", Math.round(window.scrollY + window.innerHeight / 2) + "px");
      root.classList.remove("rt-power-on");
      root.classList.add("rt-leaving");
      window.setTimeout(function () {
        window.location.assign(link.href);
        // A cancelled navigation (a "leave this page?" prompt, a file download) leaves this page in place, and a slow
        // one keeps it until the next page arrives. Either way, switch it back on as soon as the user does anything
        // (as a browser shows the old page while it waits), or after 5 s. A page that unloads never runs this.
        watchForReturn();
      }, 280);
    });

    function watchForReturn() {
      var events = ["pointerdown", "keydown", "focus"];
      var timer = window.setTimeout(restore, 5000);
      function restore() {
        window.clearTimeout(timer);
        events.forEach(function (name) {
          window.removeEventListener(name, restore, true);
        });
        root.classList.remove("rt-leaving");
      }
      events.forEach(function (name) {
        window.addEventListener(name, restore, true);
      });
    }

    // Back/forward cache restores the collapsed page; switch it back on.
    window.addEventListener("pageshow", function (event) {
      if (event.persisted) {
        root.classList.remove("rt-leaving");
      }
    });
  }

  // Elements with data-rt-reveal fade up as they scroll into view. Without motion (or without
  // IntersectionObserver) nothing is hidden in the first place.
  function setupReveal() {
    var nodes = document.querySelectorAll("[data-rt-reveal]");
    if (!nodes.length || !motionOn() || !("IntersectionObserver" in window)) {
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    root.classList.add("rt-reveal-ready");
    nodes.forEach(function (node) {
      observer.observe(node);
    });
  }

  function runIntro() {
    var tag = root.getAttribute("data-rt-intro-tag") || "";
    var logo = root.getAttribute("data-rt-intro-logo");
    var bars = "";
    for (var i = 0; i < 7; i += 1) {
      bars += "<i></i>";
    }

    var intro = document.createElement("div");
    intro.className = "rt-intro";
    intro.setAttribute("aria-hidden", "true");
    intro.innerHTML = [
      '<div class="rt-intro__screen">',
      '<div class="rt-mark">',
      '<span class="rt-mark__stripes">' + bars + "</span>",
      '<span class="rt-mark__ring"><svg viewBox="0 0 100 100" focusable="false"><circle cx="50" cy="50" r="46"></circle></svg></span>',
      '<span class="rt-mark__word"><span class="rt-mark__name rt-glitch"></span><span class="rt-mark__tag"></span></span>',
      "</div>",
      '<p class="rt-intro__skip">PRESS ANY KEY</p>',
      "</div>"
    ].join("");

    var name = intro.querySelector(".rt-mark__name");
    name.textContent = introTitle;
    name.setAttribute("data-text", introTitle);

    if (logo) {
      var img = document.createElement("img");
      img.alt = "";
      img.src = logo;
      intro.querySelector(".rt-mark__ring").appendChild(img);
      if (root.getAttribute("data-rt-intro-logo-fit") === "contain") {
        intro.querySelector(".rt-mark").classList.add("rt-mark--contain");
      }
    }

    document.body.appendChild(intro);
    try {
      introStore.setItem(INTRO_KEY, String(Date.now()));
    } catch (error) {
      // Already probed; nothing else to do.
    }

    var tagTimer = window.setTimeout(function () {
      scrambleTo(intro.querySelector(".rt-mark__tag"), tag.toUpperCase(), 14);
    }, 1250);
    var autoTimer = window.setTimeout(finish, 2700);
    var finished = false;

    function finish() {
      if (finished) {
        return;
      }
      finished = true;
      window.clearTimeout(tagTimer);
      window.clearTimeout(autoTimer);
      document.removeEventListener("keydown", finish);
      intro.classList.add("is-out");
      window.setTimeout(function () {
        root.classList.remove("rt-intro-pending");
        root.classList.add("rt-power-on");
      }, 380);
      window.setTimeout(function () {
        intro.remove();
      }, 700);
    }

    intro.addEventListener("click", finish);
    document.addEventListener("keydown", finish);
  }

  function safely(step) {
    try {
      step();
    } catch (error) {
      if (window.console) {
        window.console.warn("retro.js:", error);
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (playIntro) {
      safely(function () {
        try {
          runIntro();
        } catch (error) {
          root.classList.remove("rt-intro-pending");
          throw error;
        }
      });
    }
    safely(mountCrt);
    safely(setupGlitch);
    safely(setupNavScramble);
    safely(setupFxToggle);
    safely(setupTransitions);
    safely(setupReveal);
  });
})();
