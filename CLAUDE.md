# retro-neon-ui: guide for AI coding agents

You have been asked to give an existing application the retro-neon-ui look: a modern, responsive, accessible UI with
1980s arcade and TV-ident flair (neon tubes on black, CRT scanlines, RGB split, rainbow speed stripes, light trails,
TV power-on and power-off). Where modern convention and retro flair clash, retro wins, but never at the cost of
usability or accessibility. This file is the whole procedure. Read it top to bottom before the first edit.

## 1. Hard rules

1. **Presentation only.** Do not change application logic, data flow, API calls, routes, state, validation, element
   ids or names that scripts or tests use, `data-testid` attributes, form field names, or the order of elements that
   code depends on. Restyle by adding classes, stylesheets, resource dictionaries and wrapper elements.
2. **The app must behave exactly as before.** Run its own build and tests before you start (to know the baseline) and
   after you finish. A restyle that breaks a test is not done.
3. **Keep accessibility.** Visible focus rings, readable contrast, `prefers-reduced-motion` honoured, a reachable
   "CRT FX" switch that turns the effects off, glitch headings read once by screen readers. The kit does all of this
   if you use it as written; do not remove those parts.
4. **Logo.** The `logo/` folder is the repo owner's personal bird logo. Keep the app's own logo unless the person you
   work for asks for the bird. The kit styles any logo (round avatar, cut-out, or wordmark).
5. **Licences.** The code is MIT. The fonts are SIL OFL 1.1: copy each `OFL-*.txt` along with the font files.
6. **Ask before** replacing a light theme the app's users rely on (the kit is dark only), turning on the attract-mode
   intro in a tool people open many times a day, or restyling a screen where density or legibility is critical
   (dashboards read at a distance, data entry under time pressure). Default for line-of-business apps: no intro,
   effects on, FX switch visible.

## 2. Find the stack, pick the parts

| signal in the app | use from this repo |
|---|---|
| `package.json` with `react` (Vite, CRA, Next.js, Remix) | `web/retro.css` + `web/fonts/` + `react/` (NOT `web/retro.js`) |
| `package.json` with Vue, Svelte, Angular, Solid, or a client-side router | `web/retro.css` + `web/fonts/` + `web/retro.js` with `data-rt-transitions="off"` on `<html>` |
| server-rendered pages (ASP.NET MVC / Razor Pages, Blazor Server, Django, Flask, Rails, PHP, plain HTML) | `web/retro.css` + `web/fonts/` + `web/retro.js` |
| `tailwind.config.*` (Tailwind v3) | add `tokens/tailwind.preset.js` to `presets`, plus the web kit for components |
| `@import "tailwindcss"` in CSS (Tailwind v4) | `@import` `tokens/tailwind.theme.css` after it, plus the web kit |
| `.scss` / `.sass` files | `tokens/_tokens.scss` for variables, plus the web kit |
| `.csproj` with `<UseWPF>true</UseWPF>`, or an older project with `*.xaml` windows | `dotnet/wpf/` + `dotnet/fonts/` (also for .NET Framework) |
| `.csproj` with `<UseWindowsForms>true</UseWindowsForms>`, or an older project referencing `System.Windows.Forms`, `*.Designer.cs` | `dotnet/winforms/` + `dotnet/fonts/` (C# 7.3, also for .NET Framework) |
| Electron, Tauri, WebView2 | the web kit, chosen by the front-end framework as above |
| anything else (Qt, Swing, Flutter, a terminal UI) | `tokens/tokens.json`: copy the colours, fonts and radius by hand |

An app can match several rows (a React app with Tailwind uses both). Read `docs/stacks.md` for what each stack gets
and what it cannot do (WPF and WinForms have no glitch, intro or page transitions).

## 3. Map the app's parts to kit parts

| the app has | kit (web) | React | WPF key | WinForms |
|---|---|---|---|---|
| page background | `<html class="rt">` | `<RetroRoot>` | `Rt.Window` | `RetroTheme.Apply(form)` |
| top bar | `.rt-header` | same class | `Rt.StripeBar` under it | `StripeBar` control |
| logo + name | `.rt-brand` > `img.rt-brand-logo` + `strong` | same | `Rt.Text.Title` | role `title` |
| main navigation | `.rt-nav` > `a` (`aria-current="page"` = active) | same, `<ScrambleText>` inside | n/a | `MenuStrip` (themed) |
| side navigation | `.rt-sidebar` > `a` | same | n/a | n/a |
| primary / secondary / danger / success / neutral button | `.rt-btn .rt-btn-primary` (etc.), `.rt-btn-small` | `<NeonButton variant>` or `neonButtonClass()` | `Rt.Button.Primary` (etc.), `Rt.Button` | `SetRole(button, "primary")` |
| panel / card | `.rt-card` (+ `.rt-card-hover`, `.rt-draw`) | `<NeonCard>` | `Rt.Card` on a ContentControl | `SetRole(panel, "card")` |
| labelled input | `label.rt-field` > `span` + input; `.rt-field__hint`; `data-invalid` | `<Field>` | `Rt.Text.Label` + `Rt.TextBox` | role `label` + themed TextBox |
| bare input | `.rt-input` | same class | `Rt.TextBox`, `Rt.PasswordBox` | themed |
| checkbox / toggle | native checkbox (yellow accent) / `.rt-switch` | `<Switch>` | `Rt.CheckBox` / `Rt.Switch` | themed |
| badge / status pill | `.rt-tag` + `-accent -info -success -warning -danger` | `<Tag>` | `Rt.Tag.*` on a Label | n/a |
| message / toast | `.rt-alert` + `-success -warning -danger` | `<Alert>` | `Rt.Alert.*` on a ContentControl | n/a |
| progress | `.rt-progress` (`--rt-value`), `.rt-progress-indeterminate` | `<Progress>` | `Rt.ProgressBar` | system |
| spinner | `.rt-spinner` | `<Spinner>` | n/a | n/a |
| tabs | `.rt-tabs` > `.rt-tab[role=tab]`, `.rt-tab-panel` | `<Tabs>` | n/a | n/a |
| table | `.rt-table-wrap` > `table.rt-table`, `.rt-num` | same classes | `Rt.DataGrid` | themed DataGridView |
| modal | `dialog.rt-dialog` (+ `.rt-dialog__actions`), or `.rt-modal` > `.rt-dialog` | `<Dialog>` | n/a | n/a |
| tooltip | `.rt-tooltip` > `.rt-tooltip__tip[role=tooltip]` | same classes | `Rt.ToolTip` | n/a |
| logs / code | `.rt-terminal` (+ `.rt-terminal__bar`), `.rt-prompt`, `.rt-cursor` | `<Terminal>` | `Rt.Text.Terminal` | role `terminal` |
| breadcrumbs / pagination | `.rt-breadcrumbs`, `.rt-pagination` (`aria-current="page"`) | same classes | n/a | n/a |
| empty list | `.rt-empty` > `.rt-empty__code` + heading + text + button | same classes | n/a | n/a |
| page title | `.rt-page-header` > `h1` + `p` (status line) or `.rt-title` | `<GlitchText as="h1" className="rt-title">` | `Rt.Text.Title` | role `title` |
| hero / landing | `.rt-hero` > `.rt-kicker` + `.rt-hero-title` + `.rt-lead` + `.rt-actions`, `.rt-grid` | `<SynthGrid>`, `<IdentMark>` | n/a | n/a |
| footer | `.rt-footer` with `<span data-rt-fx-slot>` | `<FxSwitch>` in it | n/a | n/a |

`web/demo/index.html` uses every web class correctly; copy markup patterns from it. The short class names
(`.site-header .brand .nav .btn .btn-primary .card .field .tag`) style the same way; use the `rt-` names unless the
app already uses the short ones for the same parts.

## 4. Install, per stack

### Web (any framework, server-rendered or static)

1. Copy `web/retro.css`, `web/retro.js` and `web/fonts/` (keep `fonts/` next to `retro.css`; the font URLs are
   relative) into the app's static assets.
2. In the page `<head>`: `<link rel="stylesheet" href=".../retro.css">` **before** the app's own CSS, then
   `<script src=".../retro.js"></script>` **without** `defer` or `async` (it must run before first paint).
3. `<html class="rt" ...>`. Optional attributes: `data-rt-intro-title`, `data-rt-intro-tag`, `data-rt-intro-logo`,
   `data-rt-intro-logo-fit="contain"` (cut-out logos), `data-rt-fx-target` (selector, `float` or `none`),
   `data-rt-transitions="off"` (when a client-side router owns navigation). Full list: top of `web/retro.js`.
4. Wrap the page content in one element with `data-rt-shell` (the TV power-on and power-off animate it).
5. Put `<span data-rt-fx-slot></span>` where the CRT FX switch should go (footer or settings), or set
   `data-rt-fx-target="float"`. An app with its own settings screen can call `window.RetroNeon.setFx(true|false)`.
6. Add the classes from section 3 to the app's markup or templates. Delete the app's old colour and font rules only
   where they now fight the kit; keep its layout rules.

### React

1. Copy `react/RetroNeon.tsx` and `react/index.ts` into the app (e.g. `src/retro-neon/`), and `web/retro.css` +
   `web/fonts/` next to the app's global CSS. Import `retro.css` once at the entry point.
2. Wrap the app: `<RetroRoot><App /></RetroRoot>`. It sets `class="rt"` on `<html>`, tracks the FX switch and
   reduced motion, and mounts the CRT overlay. Do not load `web/retro.js` in a React app.
3. Restyle components by adding kit classes, or swap in `NeonButton`, `NeonCard`, `Field`, `Alert`, `Tabs`,
   `Dialog`, `Progress`, `Switch`, `Spinner`, `Terminal`, `Tag`, `GlitchText`. For router links styled as buttons:
   `className={neonButtonClass("primary")}`.
4. Route change animation: wrap the routed outlet in `<PowerOn routeKey={location.pathname}>`.
5. `<FxSwitch />` in the footer or settings. `useFx()` gives `[fxOn, setFx]`.
6. Next.js and other server renderers: put `className="rt"` on `<html>` in the root layout, mark files that use the
   hooks or `AttractIntro` with `"use client"`, and render `AttractIntro` only on the client.
7. Needs React 18 or newer (`useSyncExternalStore`, `useId`). Type-checked under `strict` (tests/react).

### Tailwind

v3: `presets: [require("./tokens/tailwind.preset.js")]` in `tailwind.config.js` (classes: `bg-rt-black`,
`text-rt-yellow`, `font-rt-display`, `shadow-rt-cyan`, `bg-rt-stripes`, `rt-text-glow-yellow`). v4: `@import
"./tokens/tailwind.theme.css";` after `@import "tailwindcss";` (adds `text-shadow-rt-*` and the stripe utilities).
Still load `web/retro.css` for the components and effects; Tailwind's preflight goes first, the kit after it.

### WPF

1. Copy `dotnet/wpf/RetroColors.xaml`, `RetroNeon.xaml` and `RetroNeon.Implicit.xaml` into one folder of the app
   project, e.g. `Themes\` (Build Action: Page; SDK-style projects pick them up automatically).
2. Copy `dotnet/fonts/*.ttf` into `Fonts\` at the project root with Build Action Resource:
   `<ItemGroup><Resource Include="Fonts\*.ttf" /></ItemGroup>`. If the dictionaries live in a class library instead
   of the app, change the four `Rt.Font.*` URIs in `RetroNeon.xaml` to `pack://application:,,,/LibraryName;component/Fonts/#Exo 2` (etc.).
3. `App.xaml`: `<Application.Resources><ResourceDictionary><ResourceDictionary.MergedDictionaries>
   <ResourceDictionary Source="Themes/RetroNeon.Implicit.xaml" /></ResourceDictionary.MergedDictionaries>
   </ResourceDictionary></Application.Resources>`. The Implicit file restyles every Button, TextBox, PasswordBox,
   CheckBox, ProgressBar, DataGrid, ToolTip and ScrollBar; use `RetroNeon.xaml` instead for keyed styles only.
4. Each window: `Style="{StaticResource Rt.Window}"` (implicit Window styles do not reach derived window classes).
5. Keyed styles for variants: `Rt.Button.Primary`, `Rt.Text.Title`, `Rt.Card`, `Rt.Alert.Danger`, `Rt.Switch` ...
   (full list at the top of `RetroNeon.xaml`). Scanlines: a `Rectangle` with `Style="{StaticResource Rt.Scanlines}"`
   as the last child of the window's root Grid, spanning all rows and columns.
6. Write button and tag captions in capitals (WPF has no text-transform). ComboBox, TabControl, ListBox and Menu
   keep their system templates; give them `Rt.Brush.*` colours where needed.

### WinForms

1. Add `dotnet/winforms/RetroPalette.cs`, `RetroFonts.cs` and `RetroTheme.cs` to the project.
2. Copy `dotnet/fonts/*.ttf` to `Fonts\` and copy them to the output:
   `<None Include="Fonts\*.ttf" CopyToOutputDirectory="PreserveNewest" />`.
3. `Program.Main`, before the first form: `RetroFonts.Load();`.
4. Each form's constructor, after `InitializeComponent()`: optional `RetroTheme.SetRole(control, "primary")` calls
   (buttons: primary, secondary, success, danger; labels: title, subtitle, label, terminal, muted; panels: card),
   then `RetroTheme.Apply(this);`. Add a `StripeBar` docked under the menu for the rainbow stripes.
5. What `Apply` changes (all presentation): back and fore colours of forms, labels, inputs, lists, trees, grids,
   check and radio buttons, group boxes, tab pages, up-down boxes, menus and tool strips; the font family of leaf
   controls (each keeps its size and style); buttons become flat with a neon outline; DropDownList combo boxes still
   on `DrawMode.Normal` become owner-drawn; grid row and header heights grow to fit; `card` panels get a dark fill and
   at least 16 px padding. It keeps colours the app set itself (a red error label stays red), never changes a form's
   font (that re-runs font autoscaling), changes group-box captions and tab headers only when no RichTextBox below
   them holds text (a parent font change rewrites every run of a RichTextBox), and leaves a RichTextBox that already
   holds text untouched. The full list is in the header of `RetroTheme.cs`.
6. The three files are C# 7.3: they compile in .NET Framework projects (tested as a 4.8 library) as well as .NET 8.
   TabControl tab headers, ProgressBar and DateTimePicker stay system-drawn.

### Changing colours

Edit `tokens/tokens.json`, run `python tokens/build_tokens.py`, and copy the regenerated files. Never hand-edit the
generated block in `retro.css` or the generated `.cs` / `.xaml` / `.scss` / Tailwind files.

## 5. Traps (each one has bitten before)

- **Specificity.** Every kit rule is `.rt .x`. An app override written as `.x` silently loses; write `.rt .x`.
- **Nav links are direct children only** (`.rt-nav > a`), so dropdowns nested in the nav keep their own look.
- **Glitch on plain-text headings only.** The copies repeat `textContent`; markup inside is lost. retro.js applies it
  to `.rt-brand strong`, `.rt-hero-title`, `.rt-page-header h1` and anything with `data-rt-glitch`.
- **Screen readers.** The glitch copies use `content: attr(data-text) / ""` so the heading is read once. Keep that
  line if you touch the CSS.
- **`[hidden]` always hides** (`display: none !important`), even on elements the app styles with `display: flex`.
- **Dark only.** `color-scheme: dark`. There is no light variant.
- **Button text is uppercase italic** via CSS. Long labels get wide: keep them short.
- **Pixel font (Press Start 2P) is for short labels only**, under about 0.7rem. VT323 is for status lines, nav and
  logs; body text stays Space Grotesk.
- **The CRT overlay** (`.rt-crt`) is fixed, full screen and has `pointer-events: none`; it sits at z-index 9000, the
  intro at 10000. App overlays that must sit above it need a higher z-index.
- **Box sizing.** The kit sets `box-sizing: border-box` on its own inputs; it does not reset the app's elements.
- **Client-side routers + retro.js:** set `data-rt-transitions="off"` or the TV power-off turns router links into
  full page loads.

## 6. Check before you hand it back

- [ ] The app's build and its own tests pass, the same as before the restyle.
- [ ] Every screen you touched, at desktop width and at 390 px wide: no horizontal scroll, nothing overlapping.
- [ ] Keyboard only: every control reachable, focus ring visible on each.
- [ ] Browser console: no new errors or warnings.
- [ ] With the OS set to reduced motion: no intro, nothing flashing, content visible at once.
- [ ] CRT FX switch: turns scanlines, glitch and transitions off, and the choice survives a reload.
- [ ] A screen reader (or the browser's accessibility tree) reads each glitch heading once.
- [ ] Fonts load (DevTools > Network > fonts, or `document.fonts.check('16px "Space Grotesk"')`).
- [ ] WPF / WinForms: every window opens, text is in the kit fonts (not a fallback), disabled controls look disabled.
- [ ] Give the person before and after screenshots of the main screens.

## 7. Repo map

| path | what |
|---|---|
| `web/retro.css`, `web/retro.js`, `web/fonts/` | the web kit (CSS components and effects, runtime, self-hosted fonts) |
| `web/demo/index.html` | every web component on one page: the reference implementation |
| `react/` | React 18+ components and hooks over `retro.css` |
| `tokens/` | `tokens.json` (single source) and `build_tokens.py`, plus its outputs for CSS, SCSS, Tailwind v3 and v4 |
| `dotnet/wpf/` | WPF resource dictionaries (generated `RetroColors.xaml`, `RetroNeon.xaml`, `RetroNeon.Implicit.xaml`) |
| `dotnet/winforms/` | `RetroPalette.cs` (generated), `RetroFonts.cs`, `RetroTheme.cs` |
| `dotnet/fonts/` | static TTF fonts for WPF and WinForms (with their OFL licences) |
| `logo/` | the owner's bird logo: `normal/`, `inverted/`, `web/` icons, `reference/` original, `tools/` pipeline |
| `docs/` | `flair.md` (what each effect is), `stacks.md` (per-stack notes), `screenshots/` |
| `tests/` | `run_all.py` and the checks it runs (tokens, PNG metadata, logo rebuild, React, browser, WPF, WinForms, .NET Framework compile) |
| `skill/retro-neon-ui/SKILL.md` | this guide as a Claude Code skill |
