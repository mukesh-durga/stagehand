import { AlertCircle, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, listRuns } from "@/lib/api";
import type { WorkflowRun } from "@/types";

import { RunStatusBadge } from "./RunStatusBadge";

export function RunsListPage() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRuns(await listRuns());
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? "Cannot reach the backend API."
          : "Failed to load runs.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Runs</h1>
        <p className="mt-1 text-sm text-muted-foreground">Recent workflow runs.</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading runs…
        </div>
      ) : runs.length === 0 && !error ? (
        <Card>
          <CardHeader>
            <CardTitle>No runs yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Run a workflow from the builder to see it here.
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {runs.map((run) => (
            <button
              key={run.id}
              onClick={() => navigate(`/runs/${run.id}`)}
              className="flex items-center justify-between rounded-lg border border-border bg-card p-4 text-left transition-colors hover:bg-secondary"
            >
              <div className="min-w-0">
                <div className="truncate font-mono text-sm">{run.id}</div>
                <div className="text-xs text-muted-foreground">
                  {new Date(run.created_at).toLocaleString()}
                  {run.total_latency_ms != null && ` · ${run.total_latency_ms} ms`}
                </div>
              </div>
              <RunStatusBadge status={run.status} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
