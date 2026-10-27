// Renders every export of react/index.ts on one page; tests/check_web.py loads smoke.html and checks it.
import * as React from "react";
import { createRoot } from "react-dom/client";
import {
  Alert,
  AttractIntro,
  Dialog,
  Field,
  FxSwitch,
  GlitchText,
  IdentMark,
  LightTrail,
  NeonButton,
  neonButtonClass,
  NeonCard,
  PowerOn,
  Progress,
  RetroRoot,
  ScrambleText,
  Spinner,
  Switch,
  SynthGrid,
  Tabs,
  Tag,
  Terminal,
  useFx,
} from "../../react";

const BIRD = "../../logo/normal/bird-transparent.png";

function App() {
  const [view, setView] = React.useState("one");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [fxOn] = useFx();
  const forceIntro = window.location.search.includes("intro");

  React.useEffect(() => {
    (window as unknown as { __smoke: object }).__smoke = { ready: true };
  }, []);

  return (
    <>
      <AttractIntro title="Neon App" tagline="React smoke test" logoSrc="../../logo/inverted/bird-transparent.png" logoContain force={forceIntro} />
      <header className="rt-header">
        <div className="rt-container" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.8rem 0" }}>
          <a className="rt-brand" href="#top">
            <strong>
              <GlitchText>Neon App</GlitchText>
            </strong>
          </a>
          <nav className="rt-nav" aria-label="Views">
            <a href="#one" aria-current={view === "one" ? "page" : undefined} onClick={() => setView("one")}>
              <ScrambleText>One</ScrambleText>
            </a>
            <a href="#two" aria-current={view === "two" ? "page" : undefined} onClick={() => setView("two")}>
              <ScrambleText>Two</ScrambleText>
            </a>
          </nav>
        </div>
      </header>
      <section className="rt-hero">
        <IdentMark logoSrc={BIRD} contain name="Neon" tagline="UI KIT" size="72px" className="smoke-mark" />
        <GlitchText as="h1" className="rt-hero-title">
          React
        </GlitchText>
        <SynthGrid height="160px" />
      </section>
      <main className="rt-container" style={{ display: "grid", gap: "1.2rem", padding: "2rem 0" }}>
        <PowerOn routeKey={view} id="view">
          <NeonCard draw>
            <h2 className="rt-subtitle">View {view}</h2>
            <p className="rt-status">FX {fxOn ? "on" : "off"}</p>
          </NeonCard>
        </PowerOn>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
          <NeonButton variant="primary" onClick={() => setDialogOpen(true)} id="open">
            Open dialog
          </NeonButton>
          <NeonButton variant="secondary">Secondary</NeonButton>
          <NeonButton variant="success">Success</NeonButton>
          <NeonButton variant="danger">Danger</NeonButton>
          <NeonButton small>Small</NeonButton>
          <a className={neonButtonClass("info")} href="#two">
            Link button
          </a>
        </div>
        <Field label="Email" hint="Use a full address." invalid>
          <input defaultValue="nope" id="email" />
        </Field>
        <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
          <Tag>Plain</Tag>
          <Tag accent>Accent</Tag>
          <Tag tone="success">Ok</Tag>
          <Tag tone="warning">Slow</Tag>
          <Tag tone="danger">Down</Tag>
        </div>
        <Alert title="Heads up.">Info alert.</Alert>
        <Alert tone="success">Saved.</Alert>
        <Alert tone="warning">Careful.</Alert>
        <Alert tone="danger">Failed.</Alert>
        <Progress value={40} label="Upload" />
        <Progress label="Working" />
        <Switch label="Autosave" defaultChecked />
        <Spinner />
        <Tabs
          label="Settings"
          tabs={[
            { id: "a", label: "General", content: <p>General panel</p> },
            { id: "b", label: "Display", content: <p>Display panel</p> },
          ]}
        />
        <Terminal title="build.log">{"npm run build\nok"}</Terminal>
        <LightTrail />
        <Dialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          title="Continue?"
          actions={
            <NeonButton variant="primary" onClick={() => setDialogOpen(false)} id="close">
              Close
            </NeonButton>
          }
        >
          <p>Native dialog.</p>
        </Dialog>
      </main>
      <footer className="rt-footer rt-container">
        <span>React smoke test</span>
        <FxSwitch />
      </footer>
    </>
  );
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <RetroRoot>
      <App />
    </RetroRoot>
  </React.StrictMode>
);
