import {
  Activity,
  ArrowRight,
  Boxes,
  ClipboardCheck,
  CreditCard,
  GitCompare,
  Cloud,
  Split,
  Workflow,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { enterDemo } from "@/lib/demo";

const navLinks = [
  { label: "Product", href: "#product" },
  { label: "Features", href: "#features" },
  { label: "Architecture", href: "#architecture" },
];

const features = [
  { icon: Workflow, title: "Visual workflow builder", body: "Design agents, tools, routers, and outputs on a drag-and-drop canvas." },
  { icon: Activity, title: "Live execution tracing", body: "Stream every run event in real time and highlight node status on the canvas." },
  { icon: Boxes, title: "Agent & tool nodes", body: "Model calls via a provider abstraction; safe, allow-listed tools with schemas." },
  { icon: GitCompare, title: "Replay & diff", body: "Re-run past executions and compare them node-by-node to spot regressions." },
  { icon: ClipboardCheck, title: "Eval harness", body: "Score outputs: exact-match, JSON schema, tool usage, latency, cost, LLM-judge." },
  { icon: Split, title: "Adaptive model routing", body: "A UCB bandit picks cheap vs. strong models per node from real reward signals." },
  { icon: CreditCard, title: "Usage & cost analytics", body: "Track tokens, cost, and latency across runs, models, and workflows." },
  { icon: Cloud, title: "Provider abstraction", body: "Swap model providers behind one interface — no workflow rewrites, no lock-in." },
];

const architecture = [
  { layer: "Frontend", value: "React + Vite + React Flow" },
  { layer: "API", value: "FastAPI" },
  { layer: "Execution", value: "Async worker + orchestration engine" },
  { layer: "Storage", value: "Postgres + Redis" },
  { layer: "Trace analytics", value: "ClickHouse + Postgres" },
  { layer: "Deployment", value: "Vercel + Render + Neon + Upstash" },
];

const linkButton =
  "inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border bg-transparent px-4 text-sm font-medium transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function LandingPage() {
  const navigate = useNavigate();

  const enter = () => {
    enterDemo();
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Navbar */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <a href="#product" className="flex items-center gap-2">
            <Workflow className="h-5 w-5 text-primary" />
            <span className="text-lg font-semibold tracking-tight">Stagehand</span>
          </a>
          <div className="hidden items-center gap-6 md:flex">
            {navLinks.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {l.label}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Link to="/signin" className="hidden text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline-flex sm:px-2">
              Sign In
            </Link>
            <Button size="sm" className="h-9 px-4" onClick={() => navigate("/signup")}>
              Get Started
            </Button>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section id="product" className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/10 via-background to-background" />
        <div aria-hidden className="pointer-events-none absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-primary/15 blur-3xl" />
        <div className="relative mx-auto flex max-w-4xl flex-col items-center px-6 py-24 text-center sm:py-32">
          <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-xs font-medium text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Trace-first multi-agent workflow platform
          </span>
          <h1 className="text-balance text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
            Build, run, and debug multi-agent workflows visually.
          </h1>
          <p className="mt-6 max-w-2xl text-pretty text-base text-muted-foreground sm:text-lg">
            Stagehand is a trace-first workflow platform for designing agent systems,
            executing runs, inspecting live traces, replaying failures, evaluating
            outputs, and tracking usage.
          </p>
          <div className="mt-9 flex flex-col items-center gap-3 sm:flex-row">
            <Button size="md" className="h-11 px-6 text-base shadow-lg shadow-primary/20" onClick={enter}>
              Enter
              <ArrowRight className="h-4 w-4" />
            </Button>
            <button className={`${linkButton} h-11 px-6 text-base`} onClick={() => navigate("/signup")}>
              Get Started
            </button>
            <a href="#features" className={`${linkButton} h-11 px-6 text-base`}>
              View Features
            </a>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Designed for workflow debugging, evaluation, and execution visibility.
          </p>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">Everything you need to ship agent workflows</h2>
          <p className="mt-3 text-sm text-muted-foreground">
            From visual design to live tracing, evaluation, and adaptive routing.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="rounded-lg border border-border bg-card p-5 transition-colors hover:border-primary/40"
            >
              <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/15 text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture */}
      <section id="architecture" className="border-y border-border/60 bg-card/30">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight">A clean, production-shaped architecture</h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Trace-first by design, from visual builder to execution and analytics.
            </p>
          </div>
          <div className="mx-auto grid max-w-3xl gap-3 sm:grid-cols-2">
            {architecture.map(({ layer, value }) => (
              <div key={layer} className="flex flex-col gap-1 rounded-lg border border-border bg-card p-4">
                <span className="text-xs font-medium uppercase tracking-wide text-primary">{layer}</span>
                <span className="text-sm text-foreground">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section id="start" className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Try Stagehand now</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground">
          Jump into the workspace and start building, running, and debugging workflows.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button size="md" className="h-11 px-6 text-base shadow-lg shadow-primary/20" onClick={enter}>
            Enter
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Link to="/signup" className={`${linkButton} h-11 px-6 text-base`}>
            Create an account
          </Link>
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-xs text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <Workflow className="h-4 w-4 text-primary" />
            <span>Stagehand — multi-agent workflow builder with live tracing</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/signin" className="transition-colors hover:text-foreground">Sign In</Link>
            <Link to="/signup" className="transition-colors hover:text-foreground">Sign Up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
