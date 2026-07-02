import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ApiError,
  backfillUsage,
  getBillingStatus,
  getUsageEvents,
  getUsageSummary,
} from "@/lib/api";
import type { BillingStatus, UsageEvent, UsageSummary } from "@/types";

function MetricCard({ title, value }: { title: string; value: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="text-lg font-semibold text-foreground">{value}</span>
      </CardHeader>
    </Card>
  );
}

export function UsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [events, setEvents] = useState<UsageEvent[]>([]);
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [backfilling, setBackfilling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, e, b] = await Promise.all([
        getUsageSummary(),
        getUsageEvents(),
        getBillingStatus(),
      ]);
      setSummary(s);
      setEvents(e);
      setBilling(b);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? "Cannot reach the backend API."
          : "Failed to load usage.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleBackfill = useCallback(async () => {
    setBackfilling(true);
    try {
      await backfillUsage();
      await load();
    } catch {
      setError("Failed to backfill usage.");
    } finally {
      setBackfilling(false);
    }
  }, [load]);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Usage</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Workflow run, model, and tool usage across this workspace.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
          <Button onClick={() => void handleBackfill()} disabled={backfilling}>
            {backfilling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Backfill usage
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {loading || !summary ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading usage…
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
            <MetricCard title="Runs" value={summary.total_runs} />
            <MetricCard title="Model calls" value={summary.total_model_calls} />
            <MetricCard title="Tool calls" value={summary.total_tool_calls} />
            <MetricCard title="Total tokens" value={summary.total_tokens} />
            <MetricCard
              title="Est. cost"
              value={`$${summary.total_estimated_cost_usd.toFixed(6)}`}
            />
          </div>

          {/* Billing card */}
          {billing && (
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <CardTitle>Billing</CardTitle>
                <Badge variant={billing.mode === "stripe_test" ? "success" : "muted"}>
                  {billing.mode === "stripe_test" ? "Billing enabled" : "Usage-only mode"}
                </Badge>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                {billing.mode === "stripe_test"
                  ? "Checkout is enabled for this workspace."
                  : "Usage is tracked for this workspace."}
              </CardContent>
            </Card>
          )}

          {/* Cost by model */}
          {Object.keys(summary.cost_by_model).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Cost by model</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2 text-xs">
                {Object.entries(summary.cost_by_model).map(([m, c]) => (
                  <span key={m} className="rounded bg-secondary px-2 py-1">
                    <span className="text-violet-400">{m}</span>: ${c.toFixed(6)}
                  </span>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Events table */}
          <Card>
            <CardHeader>
              <CardTitle>Usage events ({events.length})</CardTitle>
            </CardHeader>
            <CardContent className="overflow-auto">
              {events.length === 0 ? (
                <span className="text-sm text-muted-foreground">
                  No usage yet. Run a workflow, then click “Backfill usage”.
                </span>
              ) : (
                <table className="w-full text-left text-xs">
                  <thead className="text-muted-foreground">
                    <tr className="border-b border-border">
                      <th className="py-1 pr-3">type</th>
                      <th className="py-1 pr-3">model / tool</th>
                      <th className="py-1 pr-3">tokens</th>
                      <th className="py-1 pr-3">cost</th>
                      <th className="py-1 pr-3">when</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono">
                    {events.map((e) => (
                      <tr key={e.id} className="border-b border-border/50">
                        <td className="py-1 pr-3">{e.event_type}</td>
                        <td className="py-1 pr-3">{e.model_name || e.tool_name || "—"}</td>
                        <td className="py-1 pr-3">{e.total_tokens || "—"}</td>
                        <td className="py-1 pr-3">
                          {e.estimated_cost_usd ? `$${e.estimated_cost_usd.toFixed(6)}` : "—"}
                        </td>
                        <td className="py-1 pr-3 text-muted-foreground">
                          {new Date(e.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
