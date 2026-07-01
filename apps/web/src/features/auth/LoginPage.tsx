import { ArrowRight, GitCompare, Gauge, Workflow } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { enterDemo } from "@/lib/demo";

const features = [
  {
    icon: Workflow,
    title: "Visual builder",
    body: "Design multi-agent workflows on a canvas — agents, tools, routers, outputs.",
  },
  {
    icon: Gauge,
    title: "Live traces",
    body: "Watch every run stream in real time, then inspect tokens, cost, and latency.",
  },
  {
    icon: GitCompare,
    title: "Replay & eval",
    body: "Replay past runs, diff them, evaluate outputs, and track usage over time.",
  },
];

export function LoginPage() {
  const navigate = useNavigate();

  const handleEnter = () => {
    enterDemo();
    navigate("/dashboard");
  };

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-background">
      {/* Subtle gradient backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/10 via-background to-background"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-primary/15 blur-3xl"
      />

      <header className="relative z-10 flex items-center justify-between px-6 py-5 sm:px-10">
        <div className="flex items-center gap-2">
          <Workflow className="h-5 w-5 text-primary" />
          <span className="text-lg font-semibold tracking-tight">Stagehand</span>
        </div>
        <span className="rounded-full border border-border bg-card/60 px-3 py-1 text-xs text-muted-foreground">
          Live demo
        </span>
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-center px-6 py-12 text-center">
        <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-xs font-medium text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          Trace-first multi-agent workflow platform
        </span>

        <h1 className="max-w-3xl text-balance text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Build, run, and debug multi-agent workflows visually.
        </h1>

        <p className="mt-5 max-w-2xl text-pretty text-base text-muted-foreground sm:text-lg">
          Stagehand lets you design agent workflows, execute them, inspect live traces,
          replay runs, evaluate outputs, and track usage.
        </p>

        <div className="mt-8 flex flex-col items-center gap-3">
          <Button size="md" className="h-11 px-6 text-base shadow-lg shadow-primary/20" onClick={handleEnter}>
            Enter Demo
            <ArrowRight className="h-4 w-4" />
          </Button>
          <p className="text-xs text-muted-foreground">
            Free hosted demo mode uses mock models and no real charges.
          </p>
        </div>

        <div className="mt-16 grid w-full gap-4 sm:grid-cols-3">
          {features.map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="rounded-lg border border-border bg-card/70 p-5 text-left backdrop-blur-sm transition-colors hover:border-primary/40"
            >
              <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/15 text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 px-6 py-6 text-center text-xs text-muted-foreground">
        Hosted demo mode uses mock AI models and mock billing. No real charges.
      </footer>
    </div>
  );
}
