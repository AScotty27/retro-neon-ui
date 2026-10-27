---
name: retro-neon-ui
description: Use when asked to restyle, theme or "update the design" of an existing app with the retro-neon-ui look (1980s neon, CRT scanlines, rainbow speed stripes, modern accessible layout), or to build a new front end in that style. Covers web (any framework), React, Tailwind, SCSS, WPF, WinForms and Grafana dashboards.
---

# retro-neon-ui

A design kit for giving software a modern, accessible UI with 1980s arcade and TV-ident flair. Retro wins where the
two clash, never at the cost of usability or accessibility.

## Get the kit

The files live in the public repo https://github.com/AScotty27/retro-neon-ui (MIT; fonts SIL OFL). Clone it next to
the project, or download the folders you need:

```
git clone https://github.com/AScotty27/retro-neon-ui.git
```

Then read `CLAUDE.md` in the repo root in full. It is the complete procedure; this skill is its summary.

## Hard rules

1. Presentation only: never change logic, data flow, API calls, routes, state, ids, names, `data-testid`s or element
   order that code depends on.
2. The app's own build and tests must pass after the restyle exactly as before it.
3. Keep accessibility: focus rings, contrast, reduced motion, the CRT FX switch, glitch headings read once.
4. Keep the app's own logo unless the person asks for the bird in `logo/`.
5. Ship each font's `OFL-*.txt` with the font files.
6. Ask before replacing a light theme people rely on, turning on the intro in a tool opened many times a day, or
   restyling screens where density or legibility is critical.

## Steps

1. Find the stack (CLAUDE.md section 2): React = `web/retro.css` + `react/`; other web = `web/retro.css` +
   `web/retro.js` (`data-rt-transitions="off"` with a client-side router); Tailwind = `tokens/tailwind.preset.js` (v3)
   or `tokens/tailwind.theme.css` (v4) plus the web kit; SCSS = `tokens/_tokens.scss`; WPF = `dotnet/wpf/` +
   `dotnet/fonts/`; WinForms = `dotnet/winforms/` + `dotnet/fonts/`; a Grafana dashboard = export it, run
   `grafana/tools/apply_theme.py`, import the result (`grafana/README.md`; never change its queries).
2. Map the app's parts to kit parts (CLAUDE.md section 3; `web/demo/index.html` shows every web class in use).
3. Install per stack (CLAUDE.md section 4), restyle screen by screen.
4. Avoid the traps (CLAUDE.md section 5): overrides must be `.rt .x`; nav styles direct-child links only; glitch on
   plain-text headings only; `[hidden]` always hides; dark only.
5. Run the checklist (CLAUDE.md section 6) and hand over before and after screenshots.
