/* retro-neon-ui for React 18+: thin components over web/retro.css (import it once at the app root, with its fonts/
   folder next to it). Replaces web/retro.js in single-page apps: the CRT overlay, FX switch, intro, glitch, scramble
   and TV power-on are React here, so a client-side router keeps working. MIT license.

   import "retro-neon-ui/web/retro.css";            // or wherever the copied files live
   <RetroRoot>  <App/>  </RetroRoot>               // html.rt, FX state, reduced motion, CRT overlay
*/
import * as React from "react";

const FX_KEY = "rt-fx";
const FX_EVENT = "rt-fx-change";
const INTRO_KEY = "rt-intro-seen";
const GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+=?";

/** Joins class names, skipping empty ones. */
export function cx(...names: Array<string | false | null | undefined>): string {
  return names.filter(Boolean).join(" ");
}

// Probed once per page: the probe writes a key, and every write fires "storage" events in the app's other tabs.
let probed: Storage | null | undefined;

function storage(): Storage | null {
  if (probed !== undefined) {
    return probed;
  }
  try {
    const store = window.localStorage;
    store.setItem("__rt", "1");
    store.removeItem("__rt");
    probed = store;
  } catch {
    probed = null;
  }
  return probed;
}

// ---------- FX state (shared with web/retro.js through the same localStorage key) ----------

// The page's own copy of the FX choice, so the switch keeps working when storage is blocked (private mode,
// sandboxed frames). null = not read yet; another tab's change resets it.
let fxState: boolean | null = null;

function readFx(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  if (fxState === null) {
    fxState = storage()?.getItem(FX_KEY) !== "off";
  }
  return fxState;
}

function subscribeFx(onChange: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (event.key === FX_KEY || event.key === null) {
      fxState = null;
      onChange();
    }
  };
  window.addEventListener(FX_EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(FX_EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

/** Turns the CRT effects (scanlines, glitch, intro, TV transitions) on or off for this browser. */
export function setFx(on: boolean): void {
  fxState = on;
  try {
    storage()?.setItem(FX_KEY, on ? "on" : "off");
  } catch {
    // Quota full: the choice still holds for this page, it just is not remembered.
  }
  document.documentElement.classList.toggle("rt-fx-off", !on);
  window.dispatchEvent(new Event(FX_EVENT));
}

/** [fxOn, setFx]. Server render reports FX on; the client corrects it after hydration. */
export function useFx(): [boolean, (on: boolean) => void] {
  const on = React.useSyncExternalStore(subscribeFx, readFx, () => true);
  return [on, setFx];
}

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReduced(onChange: () => void): () => void {
  if (!window.matchMedia) {
    return () => undefined;
  }
  const query = window.matchMedia(REDUCED_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function readReduced(): boolean {
  return typeof window !== "undefined" && Boolean(window.matchMedia) && window.matchMedia(REDUCED_QUERY).matches;
}

/** True when the user asked the system for reduced motion. */
export function useReducedMotion(): boolean {
  return React.useSyncExternalStore(subscribeReduced, readReduced, () => false);
}

/** True when animations may run: FX on and no reduced-motion preference. */
export function useMotionOn(): boolean {
  const [fxOn] = useFx();
  const reduced = useReducedMotion();
  return fxOn && !reduced;
}

// ---------- Root, CRT overlay, FX switch ----------

export interface RetroRootProps {
  children?: React.ReactNode;
  /** Render the scanline overlay (default true). It hides itself when FX is off. */
  crt?: boolean;
}

/** Puts class "rt" (and rt-fx-off / rt-reduced) on <html> and mounts the CRT overlay. Render it once, at the top. */
export function RetroRoot({ children, crt = true }: RetroRootProps) {
  const [fxOn] = useFx();
  const reduced = useReducedMotion();
  React.useEffect(() => {
    const root = document.documentElement;
    root.classList.add("rt");
    root.classList.toggle("rt-fx-off", !fxOn);
    root.classList.toggle("rt-reduced", reduced);
  }, [fxOn, reduced]);
  return (
    <>
      {children}
      {crt ? <CrtOverlay /> : null}
    </>
  );
}

/** Scanlines, vignette, noise and the rolling refresh band. Decorative; pointer events pass through. */
export function CrtOverlay() {
  return (
    <div className="rt-crt" aria-hidden="true">
      <span className="rt-crt__roll" />
    </div>
  );
}

export interface FxSwitchProps {
  className?: string;
  /** Fixed in the bottom-right corner instead of in the flow (for apps with no footer). */
  floating?: boolean;
}

/** The "CRT FX ON/OFF" button. Put it in the footer or a settings menu. */
export function FxSwitch({ className, floating }: FxSwitchProps) {
  const [fxOn, set] = useFx();
  return (
    <button
      type="button"
      className={cx("rt-fx-toggle", floating && "rt-fx-toggle--float", className)}
      aria-pressed={fxOn}
      onClick={() => set(!fxOn)}
    >
      {fxOn ? "CRT FX ON" : "CRT FX OFF"}
    </button>
  );
}

// ---------- Text effects ----------

export interface GlitchTextProps extends React.HTMLAttributes<HTMLElement> {
  /** Element to render, e.g. "h1" (default "span"). */
  as?: React.ElementType;
  /** Plain text only: the glitch copies repeat it, so markup inside would be lost. */
  children: string;
}

/** RGB-split glitch: magenta and cyan slices flash every few seconds, constantly on hover. Read once by screen readers. */
export function GlitchText({ as: Tag = "span", children, className, ...rest }: GlitchTextProps) {
  return (
    <Tag {...rest} className={cx("rt-glitch", className)} data-text={children}>
      {children}
    </Tag>
  );
}

export interface ScrambleOptions {
  /** Frames of random glyphs before the text settles (about 32 ms each). */
  frames?: number;
  /** Bump this (a counter, a hover flag) to replay the scramble. */
  trigger?: unknown;
  /** Also scramble once when the component mounts (default false). */
  onMount?: boolean;
}

/** Returns `text`, decoding from random glyphs each time `trigger` changes (not on mount unless `onMount`).
    Static when motion is off. */
export function useScramble(text: string, { frames = 9, trigger, onMount = false }: ScrambleOptions = {}): string {
  const motionOn = useMotionOn();
  const [out, setOut] = React.useState(text);
  const last = React.useRef<{ trigger: unknown } | null>(null);
  // Forget the last trigger on unmount, so a remount (including StrictMode's test remount) counts as a mount again.
  React.useEffect(
    () => () => {
      last.current = null;
    },
    []
  );
  React.useEffect(() => {
    const first = last.current === null;
    const changed = !first && !Object.is(last.current?.trigger, trigger);
    last.current = { trigger };
    if (!motionOn || !(changed || (first && onMount))) {
      setOut(text);
      return undefined;
    }
    let frame = 0;
    const timer = window.setInterval(() => {
      frame += 1;
      const settled = Math.floor((text.length * frame) / frames);
      let next = "";
      for (let i = 0; i < text.length; i += 1) {
        const ch = text.charAt(i);
        next += i < settled || ch === " " ? ch : GLYPHS.charAt(Math.floor(Math.random() * GLYPHS.length));
      }
      setOut(frame >= frames ? text : next);
      if (frame >= frames) {
        window.clearInterval(timer);
      }
    }, 32);
    return () => window.clearInterval(timer);
  }, [text, frames, trigger, motionOn, onMount]);
  return out;
}

/** Text that scrambles on mouse hover only (nav links), so keyboard and screen-reader users never meet
    half-scrambled text: assistive technology reads the real text from a visually hidden copy. */
export function ScrambleText({ children, frames = 9 }: { children: string; frames?: number }) {
  const [hovers, setHovers] = React.useState(0);
  const shown = useScramble(children, { frames, trigger: hovers });
  return (
    <span onMouseEnter={() => setHovers((n) => n + 1)}>
      <span className="rt-sr-only">{children}</span>
      <span aria-hidden="true">{shown}</span>
    </span>
  );
}

// ---------- Components ----------

export type NeonVariant = "primary" | "secondary" | "info" | "success" | "danger" | "neutral";

/** Class string for a neon button, for any element: <Link className={neonButtonClass("primary")}>. */
export function neonButtonClass(variant: NeonVariant = "neutral", small = false, className?: string): string {
  return cx("rt-btn", `rt-btn-${variant}`, small && "rt-btn-small", className);
}

export interface NeonButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: NeonVariant;
  small?: boolean;
}

/** Slanted neon-tube button with a rainbow drop on hover. */
export const NeonButton = React.forwardRef<HTMLButtonElement, NeonButtonProps>(function NeonButton(
  { variant = "neutral", small = false, className, type = "button", ...rest },
  ref
) {
  return <button ref={ref} type={type} className={neonButtonClass(variant, small, className)} {...rest} />;
});

export interface NeonCardProps extends React.HTMLAttributes<HTMLElement> {
  as?: React.ElementType;
  /** Trace the neon beam around the border once, on mount. */
  draw?: boolean;
  /** Lift and glow on hover (for clickable cards). */
  hover?: boolean;
}

/** Dark panel with a rainbow stripe cap. */
export function NeonCard({ as: Tag = "div", draw, hover, className, ...rest }: NeonCardProps) {
  return <Tag {...rest} className={cx("rt-card", draw && "rt-draw", hover && "rt-card-hover", className)} />;
}

export interface FieldProps {
  label: React.ReactNode;
  hint?: React.ReactNode;
  invalid?: boolean;
  /** One input, select or textarea. Its aria-describedby and aria-invalid are filled in. */
  children: React.ReactElement<{ "aria-describedby"?: string; "aria-invalid"?: boolean }>;
  className?: string;
}

/** Label in pixel caps above a dark neon input. */
export function Field({ label, hint, invalid, children, className }: FieldProps) {
  const hintId = React.useId();
  const control = React.isValidElement(children)
    ? React.cloneElement(children, {
        "aria-describedby": hint ? cx(children.props["aria-describedby"], hintId) : children.props["aria-describedby"],
        "aria-invalid": invalid || children.props["aria-invalid"] || undefined,
      })
    : children;
  return (
    <label className={cx("rt-field", className)} data-invalid={invalid ? "" : undefined}>
      <span>{label}</span>
      {control}
      {hint ? (
        <small className="rt-field__hint" id={hintId}>
          {hint}
        </small>
      ) : null}
    </label>
  );
}

export type Tone = "info" | "success" | "warning" | "danger";

export function Tag({ tone, accent, className, ...rest }: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone; accent?: boolean }) {
  return <span {...rest} className={cx("rt-tag", tone && `rt-tag-${tone}`, accent && "rt-tag-accent", className)} />;
}

export interface AlertProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  tone?: Tone;
  title?: React.ReactNode;
}

/** Tinted message box with a pixel label (INFO, OK, WARN, ERROR). Danger alerts are announced at once. */
export function Alert({ tone = "info", title, children, className, role, ...rest }: AlertProps) {
  return (
    <div
      {...rest}
      role={role ?? (tone === "danger" ? "alert" : "status")}
      className={cx("rt-alert", tone !== "info" && `rt-alert-${tone}`, className)}
    >
      <span>
        {title ? <strong>{title} </strong> : null}
        {children}
      </span>
    </div>
  );
}

export interface ProgressProps {
  /** 0 to 100; leave out for an indeterminate (busy) bar. */
  value?: number;
  label: string;
  className?: string;
}

/** 80s level meter: rainbow LED segments fill left to right. */
export function Progress({ value, label, className }: ProgressProps) {
  const known = typeof value === "number" && Number.isFinite(value);
  const pct = known ? Math.min(100, Math.max(0, value as number)) : 0;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={known ? 0 : undefined}
      aria-valuemax={known ? 100 : undefined}
      aria-valuenow={known ? Math.round(pct) : undefined}
      className={cx("rt-progress", !known && "rt-progress-indeterminate", className)}
      style={{ "--rt-value": `${pct}%` } as React.CSSProperties}
    />
  );
}

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "role"> {
  label: React.ReactNode;
}

/** On/off switch over a real checkbox (role="switch"), so forms and screen readers treat it as one. */
export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(function Switch({ label, className, ...rest }, ref) {
  return (
    <label className={cx("rt-switch", className)}>
      <input ref={ref} type="checkbox" role="switch" {...rest} /> <span>{label}</span>
    </label>
  );
});

export function Spinner({ label = "Loading", size }: { label?: string; size?: string }) {
  return (
    <span className="rt-spinner" role="status" style={size ? ({ "--rt-spinner-size": size } as React.CSSProperties) : undefined}>
      <span className="rt-sr-only">{label}</span>
    </span>
  );
}

/** Green phosphor code block with a title bar. */
export function Terminal({ title, children }: { title?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rt-terminal">
      {title ? (
        <div className="rt-terminal__bar">
          <span>{title}</span>
        </div>
      ) : null}
      <pre>
        <code>{children}</code>
      </pre>
    </div>
  );
}

export interface TabItem {
  id: string;
  label: React.ReactNode;
  content: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  /** Accessible name of the tab list. */
  label: string;
  value?: string;
  defaultValue?: string;
  onChange?: (id: string) => void;
}

/** Tabs with arrow-key, Home and End navigation; the active tab gets the stripe underline. */
export function Tabs({ tabs, label, value, defaultValue, onChange }: TabsProps) {
  const [inner, setInner] = React.useState(defaultValue ?? tabs[0]?.id);
  const active = value ?? inner;
  const base = React.useId();
  const refs = React.useRef<Array<HTMLButtonElement | null>>([]);

  function select(index: number) {
    const tab = tabs[(index + tabs.length) % tabs.length];
    if (!tab) {
      return;
    }
    setInner(tab.id);
    onChange?.(tab.id);
    refs.current[(index + tabs.length) % tabs.length]?.focus();
  }

  function onKeyDown(event: React.KeyboardEvent, index: number) {
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
    if (event.key in moves) {
      event.preventDefault();
      select(moves[event.key]);
    }
  }

  return (
    <div>
      <div className="rt-tabs" role="tablist" aria-label={label}>
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            ref={(node) => {
              refs.current[i] = node;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${tab.id}`}
            aria-selected={tab.id === active}
            aria-controls={`${base}-panel-${tab.id}`}
            tabIndex={tab.id === active ? 0 : -1}
            className="rt-tab"
            onClick={() => select(i)}
            onKeyDown={(event) => onKeyDown(event, i)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`${base}-panel-${tab.id}`}
          aria-labelledby={`${base}-tab-${tab.id}`}
          className="rt-tab-panel"
          hidden={tab.id !== active}
          tabIndex={0}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  children?: React.ReactNode;
  /** Buttons, right-aligned under the content. */
  actions?: React.ReactNode;
}

/** Modal on the native <dialog> (focus trap, Escape and backdrop from the browser); powers on like an old TV. */
export function Dialog({ open, onClose, title, children, actions }: DialogProps) {
  const ref = React.useRef<HTMLDialogElement>(null);
  const titleId = React.useId();
  React.useEffect(() => {
    const dialog = ref.current;
    if (!dialog) {
      return;
    }
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);
  return (
    <dialog ref={ref} className="rt-dialog" aria-labelledby={titleId} onClose={onClose}>
      <h2 id={titleId}>{title}</h2>
      {children}
      {actions ? <div className="rt-dialog__actions">{actions}</div> : null}
    </dialog>
  );
}

// ---------- Ident pieces ----------

export interface IdentMarkProps {
  /** Image inside the neon ring. */
  logoSrc?: string;
  /** Show a transparent cut-out logo whole instead of cropped round. */
  contain?: boolean;
  name?: string;
  tagline?: string;
  /** Give the name the RGB-split glitch. */
  glitchName?: boolean;
  /** CSS length, e.g. "96px" (default) or "clamp(64px, 9vw, 92px)". */
  size?: string;
  className?: string;
}

/** Speed stripes + a neon ring drawn around the logo (+ optional flickering wordmark): the TV-ident composition. */
export function IdentMark({ logoSrc, contain, name, tagline, glitchName, size, className }: IdentMarkProps) {
  return (
    <div
      className={cx("rt-mark", contain && "rt-mark--contain", className)}
      style={size ? ({ "--rt-mark-size": size } as React.CSSProperties) : undefined}
    >
      <span className="rt-mark__stripes" aria-hidden="true">
        {Array.from({ length: 7 }, (_, i) => (
          <i key={i} />
        ))}
      </span>
      <span className="rt-mark__ring">
        <svg viewBox="0 0 100 100" aria-hidden="true" focusable="false">
          <circle cx="50" cy="50" r="46" />
        </svg>
        {logoSrc ? <img src={logoSrc} alt="" /> : null}
      </span>
      {name !== undefined || tagline !== undefined ? (
        <span className="rt-mark__word">
          {name !== undefined ? (
            <span className={cx("rt-mark__name", glitchName && "rt-glitch")} data-text={glitchName ? name : undefined}>
              {name}
            </span>
          ) : null}
          {tagline !== undefined ? <span className="rt-mark__tag">{tagline}</span> : null}
        </span>
      ) : null}
    </div>
  );
}

/** Synthwave perspective floor; place it inside a position:relative hero (it sits at the bottom, behind content). */
export function SynthGrid({ height }: { height?: string }) {
  return (
    <div className="rt-grid" aria-hidden="true" style={height ? ({ "--rt-grid-height": height } as React.CSSProperties) : undefined} />
  );
}

/** Three-line light trail divider. */
export function LightTrail({ className }: { className?: string }) {
  return <span className={cx("rt-trail", className)} aria-hidden="true" />;
}

// ---------- Intro and route power-on ----------

export interface AttractIntroProps {
  title: string;
  tagline?: string;
  logoSrc?: string;
  /** Show a transparent cut-out logo whole instead of cropped round. */
  logoContain?: boolean;
  /** Minimum hours between plays in one browser (default 12). */
  gapHours?: number;
  /** Play even if it played recently (a "replay intro" button). */
  force?: boolean;
  onDone?: () => void;
}

function introDue(gapHours: number, force: boolean, motionOn: boolean): boolean {
  if (typeof window === "undefined" || !motionOn) {
    return false;
  }
  const store = storage();
  if (!store) {
    return false;
  }
  const since = Date.now() - (Number(store.getItem(INTRO_KEY)) || 0);
  // A stamp from the future (clock moved back) counts as stale rather than blocking the intro.
  return force || since < 0 || since > gapHours * 3600 * 1000;
}

/** Attract-mode ident: stripes sweep in, the ring draws, the logo pops, the name flickers on, the tagline decodes,
    then the screen collapses like an old TV and the page powers on. Any key or click skips it. At most every
    `gapHours` per browser; never with reduced motion or FX off. Client-rendered apps only (it decides on first render). */
export function AttractIntro({ title, tagline = "", logoSrc, logoContain, gapHours = 12, force = false, onDone }: AttractIntroProps) {
  const motionOn = useMotionOn();
  const [phase, setPhase] = React.useState<"play" | "out" | "done">(() =>
    introDue(gapHours, force, readFx() && !readReduced()) ? "play" : "done"
  );
  const [tagRun, setTagRun] = React.useState(0);
  const tag = useScramble(tagline.toUpperCase(), { frames: 14, trigger: tagRun });
  const doneRef = React.useRef(onDone);
  doneRef.current = onDone;

  React.useEffect(() => {
    if (phase !== "play") {
      return undefined;
    }
    try {
      storage()?.setItem(INTRO_KEY, String(Date.now()));
    } catch {
      // Already probed.
    }
    const finish = () => setPhase((p) => (p === "play" ? "out" : p));
    const tagTimer = window.setTimeout(() => setTagRun((n) => n + 1), 1250);
    const autoTimer = window.setTimeout(finish, 2700);
    document.addEventListener("keydown", finish);
    return () => {
      window.clearTimeout(tagTimer);
      window.clearTimeout(autoTimer);
      document.removeEventListener("keydown", finish);
    };
  }, [phase]);

  React.useEffect(() => {
    if (phase !== "out") {
      return undefined;
    }
    const handOver = window.setTimeout(() => {
      const root = document.documentElement;
      root.classList.remove("rt-power-on");
      void root.offsetWidth;
      root.classList.add("rt-power-on");
      doneRef.current?.();
    }, 380);
    const unmount = window.setTimeout(() => setPhase("done"), 700);
    return () => {
      window.clearTimeout(handOver);
      window.clearTimeout(unmount);
    };
  }, [phase]);

  if (phase === "done" || !motionOn) {
    return null;
  }
  return (
    <div className={cx("rt-intro", phase === "out" && "is-out")} aria-hidden="true" onClick={() => setPhase("out")}>
      <div className="rt-intro__screen">
        <IdentMark logoSrc={logoSrc} contain={logoContain} name={title} tagline={tagRun ? tag : ""} glitchName />
        <p className="rt-intro__skip">PRESS ANY KEY</p>
      </div>
    </div>
  );
}

export interface PowerOnProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Change this (the route path) to replay the TV power-on; the wrapper remounts its children. */
  routeKey: string;
}

/** Route wrapper: each new routeKey switches the view on like an old TV. Skipped with FX off or reduced motion. */
export function PowerOn({ routeKey, className, ...rest }: PowerOnProps) {
  return <div key={routeKey} {...rest} className={cx("rt-tv-on", className)} />;
}
