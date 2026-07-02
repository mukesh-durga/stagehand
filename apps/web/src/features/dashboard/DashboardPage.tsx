import { AlertCircle, ArrowRight, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { dbHealthCheck, healthCheck } from "@/lib/api";
import { useAppStore } from "@/stores/appStore";

const metricCards = [
  { title: "Workflows", value: "—", hint: "Clone a template to create one" },
  { title: "Runs", value: "—", hint: "Run a workflow to see runs" },
  { title: "Failed Runs", value: "—", hint: "Nothing failed yet" },
  { title: "Token Cost", value: "$0.00", hint: "Estimated across all runs" },
];

const gettingStarted = [
  { step: 1, title: "Open Templates", body: "Browse the gallery of ready-made workflows." },
  { step: 2, title: "Clone a workflow", body: "Copy a template into an editable workflow." },
  { step: 3, title: "Run it", body: "Execute the workflow and watch traces stream live." },
  { step: 4, title: "Inspect traces & usage", body: "Review tokens, cost, latency, and evals." },
];

export function DashboardPage() {
  const { backendStatus, dbStatus, setBackendStatus, setDbStatus } = useAppStore();
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    setError(null);
    setBackendStatus("checking");
    setDbStatus("checking");

    try {
      const health = await healthCheck();
      setBackendStatus(health.status === "ok" ? "online" : "offline");
    } catch {
      setBackendStatus("offline");
      setDbStatus("offline");
      setError("Cannot reach the backend API. Is it running on the configured URL?");
      return;
    }

    try {
      const db = await dbHealthCheck();
      setDbStatus(db.database === "connected" ? "online" : "offline");
    } catch {
      setDbStatus("offline");
    }
  }, [setBackendStatus, setDbStatus]);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          A trace-first multi-agent workflow platform — visually design AI workflows,
          run them asynchronously, and debug every run through live execution traces.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {metricCards.map((m) => (
          <Card key={m.title} className="transition-colors hover:border-primary/40">
            <CardHeader className="gap-2">
              <CardTitle>{m.title}</CardTitle>
              <span className="text-2xl font-semibold text-foreground">{m.value}</span>
              <span className="text-xs text-muted-foreground">{m.hint}</span>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-foreground">Getting started</CardTitle>
            <Link
              to="/templates"
              className="inline-flex h-8 items-center gap-2 rounded-md border border-border bg-transparent px-3 text-sm font-medium transition-colors hover:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Open Templates
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {gettingStarted.map(({ step, title, body }) => (
              <div key={step} className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
                  {step}
                </span>
                <div>
                  <p className="text-sm font-medium">{title}</p>
                  <p className="text-xs text-muted-foreground">{body}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-foreground">System status</CardTitle>
            <Button size="sm" variant="outline" onClick={() => void checkHealth()}>
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Backend API</span>
              <StatusBadge status={backendStatus} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm">Database</span>
              <StatusBadge status={dbStatus} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
