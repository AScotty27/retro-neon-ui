# Per-stack notes

What each stack gets, what it cannot do, and how it was tested. Install steps are in [CLAUDE.md](../CLAUDE.md)
section 4.

## Web (`web/`)

Everything: every component and every effect in [flair.md](flair.md). `retro.css` is framework-free CSS scoped under
`html.rt`; `retro.js` is dependency-free ES5 for multi-page sites and server-rendered apps. Current browsers only:
it uses `color-mix()`, `@property`, CSS masks and `content: ... / ""` alt text. The automated checks run in Chromium;
Firefox and Safari were not tested.

Tested by `tests/check_web.py` (Playwright, Chromium): the demo page at 1440x900 and 390x844, fonts loaded, images
decoded, no horizontal scroll, every reveal card revealed, glitch heading read once in the accessibility tree,
`[hidden]`, tabs (click and arrow keys), dialog (open, Escape), form, a cancelled "leave this page?" navigation
powering the page back on, FX switch (off, survives reload, hides CRT, script API), intro (plays once, hides the page while it plays, skippable, `?rt-intro` forces it, never under reduced
motion), zero console errors (with a planted-error control).

## React (`react/`)

`RetroNeon.tsx` replaces `retro.js` with React state, so client-side routers keep working: `RetroRoot` (html class,
FX state, reduced motion, CRT overlay), `FxSwitch`, `AttractIntro`, `PowerOn` (route power-on), `GlitchText`,
`ScrambleText` / `useScramble`, `NeonButton` / `neonButtonClass`, `NeonCard`, `Field`, `Tag`, `Alert`, `Progress`,
`Switch`, `Spinner`, `Terminal`, `Tabs`, `Dialog` (native `<dialog>`), `IdentMark`, `SynthGrid`, `LightTrail`, and the
hooks `useFx`, `useReducedMotion`, `useMotionOn`. React 18 or newer. The FX choice is shared with `retro.js` (same
storage key). Server rendering: `AttractIntro` decides on the first client render, so render it client-only.

Tested by `tests/react/` (strict `tsc --noEmit` against React 18.3 types, esbuild bundle) and `tests/check_web.py`
(the bundle rendered in Chromium under `StrictMode`: intro, CRT, fonts, Field hint wiring, Progress value, Dialog,
Tabs keys, PowerOn re-mount, FxSwitch and `useFx` re-render, FX survives reload, two open tabs stay quiet and stay in
sync, the switch works with storage blocked, zero console errors). Also run against React 19.2 (types, bundle,
browser checks): all pass.

## Tokens (`tokens/`)

`tokens.json` is the single source. `build_tokens.py` (standard library only) writes `tokens.css`, the `:root` block
inside `web/retro.css`, `_tokens.scss`, `tailwind.preset.js` (v3), `tailwind.theme.css` (v4), `RetroPalette.cs` and
`RetroColors.xaml`; `--check` fails when any is stale. Tested: `--check` after a build reports every file up to date;
the generated `:root` block reproduces every value of the hand-written original; Tailwind 3.4 and 4.1 builds emit
every documented class (including opacity modifiers like `bg-rt-c1/50`); Dart Sass compiles `@use "tokens"`.

## WPF (`dotnet/wpf/`, `dotnet/fonts/`)

Palette brushes, the stripe and trail gradients, glow effects, scanline and LED-segment brushes, the four fonts, and
styles for Window, TextBlock (title, subtitle, label, terminal, body, muted), Button (neutral, primary, secondary,
success, danger: slanted tube with the rainbow drop on hover), TextBox, PasswordBox (focus halo), CheckBox, switch
(ToggleButton or CheckBox), ProgressBar (level meter), card, alerts, tags, DataGrid, ScrollBar and ToolTip.
`RetroNeon.Implicit.xaml` makes them the defaults app-wide.

Cannot do: the glitch, scramble, intro and page transitions (web-only motion); `text-transform` (write captions in
capitals). ComboBox, TabControl, ListBox, TreeView and Menu keep their system templates (use the brushes on them).

Fonts: `dotnet/fonts/` holds static files, one per weight, which WPF and GDI+ load as ordinary faces. They are
instances of the upstream variable fonts made with fontTools (Exo 2 Black Italic and ExtraBold Italic, Space Grotesk Regular, Medium and
Bold; both families have no Reserved Font Name) plus the unmodified Press Start 2P and VT323 files.

Tested by `tests/wpf/` (.NET 8; `tests/netfx/` also compiles them for .NET Framework 4.8): the dictionaries compile as Pages, every font key resolves to its shipped TTF (not
a fallback), 37 resource keys found, and a sample of every style renders offscreen with `RenderTargetBitmap` (no
window): `docs/screenshots/wpf-sample.png`.

## WinForms (`dotnet/winforms/`)

`RetroPalette` (generated colours, stripes, font names), `RetroFonts` (loads the TTFs into a PrivateFontCollection
AND registers them with GDI, because Label and Button draw through GDI and would otherwise silently fall back to a
system font), `RetroTheme.Apply` (form, buttons with roles, text boxes, owner-drawn dark combo boxes, list and tree
views, grids, check and radio buttons, group boxes, labels with roles, menus and tool strips through `RetroColorTable`,
card panels) and the `StripeBar` control.

Cannot do: glows, slanted buttons, scanlines and any motion (plain WinForms has no compositing); ProgressBar and
TabControl stay system-drawn.

What `Apply` leaves alone, on purpose: the form's font (changing it re-runs font autoscaling; leaf controls get the
kit's font family at their own size and style instead), group-box caption and tab-header fonts when a RichTextBox below
them holds text (a parent's font change rewrites every run of a RichTextBox), colours the app set itself, any
RichTextBox that already holds text, and the inner parts of up-down boxes.

Tested by `tests/winforms/` (.NET 8): all six font families load, GDI text with each kit font differs from its
fallback (so the font is really used), the combo box owner-draw paints the dark background and the text, an
app-coloured label keeps its colour, italic and underlined labels keep their style, a grid keeps its own cell font,
a filled RichTextBox's RTF is byte-identical after `Apply` (also inside a group box), an empty one is themed, group
captions turn to the kit font without leaking bold into their children, tab pages and NumericUpDown turn dark (with
no second border on the inner edit box), the primary button gets the accent colour, and a themed form renders
offscreen with `DrawToBitmap` (never shown): `docs/screenshots/winforms-sample.png` (combo boxes do not print
offscreen, so the sample has none). `tests/netfx/` compiles all three files and the WPF dictionaries as a .NET
Framework 4.8 library with C# 7.3, warnings as errors.

## Logo (`logo/`)

See the README's logo section. `tests/check_logo.py` rebuilds the whole set from `logo/reference/original-bird.png`
into a temporary folder and byte-compares all 31 files with the shipped ones; `tests/check_png_chunks.py` confirms
every PNG and ICO frame carries pixel data only (with a planted-chunk control).
