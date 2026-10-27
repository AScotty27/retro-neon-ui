# The flair, piece by piece

The look comes from 1980s TV station idents and arcade attract screens, applied to a modern layout. Each effect, where
it lives in the kit, and how to turn it off.

| effect | what it looks like | web kit | React | off switch |
|---|---|---|---|---|
| neon tube type | yellow, cyan and green text with a white-hot core and a soft halo | `--rt-glow-*` text-shadows on titles, labels, status lines | same classes | none (static) |
| RGB split | magenta and cyan fringes either side of headings | `--rt-split` | same | none (static) |
| glitch | magenta and cyan slices of a heading flash for about 0.3 s every 7 s, constantly on hover | `.rt-glitch` + `data-text` (retro.js adds them) | `<GlitchText>` | FX switch, reduced motion |
| speed stripes | seven slanted capsule bars, violet to lime | `.rt-mark__stripes`, `.rt-brand::before`, `--rt-stripes` caps on cards, header, tabs | `<IdentMark>` | none (static) |
| neon ring | a ring drawn around the logo, then the logo pops in | `.rt-mark__ring` (SVG stroke draw) | `<IdentMark>` | reduced motion (ends drawn) |
| light trail | three thin glowing lines under titles and above the footer | `.rt-trail`, `.rt-page-header::after`, `.rt-footer::before` | `<LightTrail>` | reduced motion (ends drawn) |
| CRT screen | scanlines, vignette, film noise and a slow rolling refresh band over the whole page | `.rt-crt` overlay (retro.js mounts it) | `<CrtOverlay>` (in `RetroRoot`) | FX switch hides it; reduced motion stops the noise and roll |
| TV power-on / off | the page collapses to a bright line and out on link clicks, and powers on at load | `.rt-power-on`, `.rt-leaving` on `[data-rt-shell]` | `<PowerOn>` (route changes) | FX switch, reduced motion, `data-rt-transitions="off"` |
| attract-mode intro | stripes sweep in, ring draws, logo pops, name flickers on, tagline decodes, screen collapses into the page | `data-rt-intro-title` on `<html>` | `<AttractIntro>` | at most every 12 hours per browser, any key or click skips, never with FX off or reduced motion |
| text scramble | nav labels decode from random glyphs on mouse hover | retro.js on `.rt-nav > a` | `<ScrambleText>`, `useScramble()` | FX switch, reduced motion; never on keyboard focus |
| chrome title | white-to-horizon-to-pink metallic italic fill with a neon halo | `.rt-hero-title` | same class | none (static) |
| synthwave floor | a perspective grid scrolling toward the viewer under the hero | `.rt-grid` | `<SynthGrid>` | reduced motion stops it |
| slanted neon buttons | skewed tubes; a rainbow block drops behind on hover | `.rt-btn` + variants | `<NeonButton>` | none (hover only) |
| card beam | a neon beam traces the card border once when it scrolls in | `.rt-card` + `data-rt-reveal` or `.rt-draw` | `<NeonCard draw>` | reduced motion |
| level meter | progress as rainbow LED segments | `.rt-progress` | `<Progress>` | none (static) |
| arcade selector | a blinking `▶` beside the active nav item, sidebar link and hovered table row | `.rt-nav`, `.rt-sidebar`, `.rt-table` | same classes | reduced motion stops the blink |
| blinking block cursor | a `█` after status lines | `.rt-status`, `.rt-cursor`, `.rt-page-header p` | same classes | reduced motion |

## The modern side

- Responsive grids, a sticky blurred header, no horizontal scroll at 390 px.
- Real focus rings (2 px cyan) on everything focusable.
- `prefers-reduced-motion: reduce` makes every animation jump to its end state: nothing loops, flashes or slides.
- The CRT FX switch (footer, settings, or floating) turns off scanlines, glitch, intro and transitions, and the
  choice is remembered per browser (`localStorage` key `rt-fx`, shared by retro.js and the React layer).
- Decorative copies and glyphs carry empty alt text (`content: ... / ""`), so screen readers read each heading once.
- `[hidden]` always hides.
- Fonts are self-hosted (no requests to third-party font servers) and load with `font-display: swap`.

## Palette

| token | value | use |
|---|---|---|
| black | `#050409` | page background |
| ink / ink-2 | `#0c0a16` / `#15112a` | panels |
| text / muted | `#f6f3ff` / `#aba4cd` | body text / secondary text |
| line | `rgba(166, 61, 255, 0.3)` | borders |
| c1 to c7 | `#4d5bff` `#a63dff` `#ff2e9a` `#ff3b3b` `#ff8c1a` `#ffd60a` `#9dff2e` | the speed stripes |
| cyan / yellow / red / green | `#2de2ff` / `#ffef5c` / `#ff4d5e` / `#5dff8f` | info and labels / titles and accent / danger / success and terminal |

Fonts: Exo 2 (display, italic 800 to 900), Space Grotesk (body), Press Start 2P (pixel labels), VT323 (terminal).
Single source: `tokens/tokens.json`.
