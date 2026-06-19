import { AlertCircle, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { dbHealthCheck, healthCheck } from "@/lib/api";
import { useAppStore } from "@/stores/appStore";

const metricCards = [
  { title: "Workflows", value: "—" },
  { title: "Runs", value: "—" },
  { title: "Failed Runs", value: "—" },
  { title: "Token Cost", value: "—" },
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
      <div>
        <h1 className="text-2xl font-semibold">Stagehand</h1>
        <p className="mt-1 text-sm text-muted-foreground">
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

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>System status</CardTitle>
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

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {metricCards.map((m) => (
          <Card key={m.title}>
            <CardHeader>
              <CardTitle>{m.title}</CardTitle>
              <span className="text-2xl font-semibold text-foreground">{m.value}</span>
            </CardHeader>
          </Card>
        ))}
      </div>

      <p className="text-xs text-muted-foreground">
        This is the frontend foundation stage (Milestone 3). Metrics are placeholders;
        the workflow builder and live tracing arrive in later milestones.
      </p>
    </div>
  );
}
