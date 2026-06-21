import { AlertCircle, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, getRoutingStats } from "@/lib/api";
import type { RoutingStat } from "@/types";

export function RoutingPage() {
  const [stats, setStats] = useState<RoutingStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStats(await getRoutingStats());
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? "Cannot reach the backend API."
          : "Failed to load routing stats.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Adaptive routing</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Adaptive routing uses UCB to balance exploration and exploitation across cheap
          and strong models. Stats update when a run with an adaptive agent is evaluated.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading routing stats…
        </div>
      ) : stats.length === 0 && !error ? (
        <Card>
          <CardHeader>
            <CardTitle>No routing stats yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Run a workflow whose Agent node uses <code>adaptive</code> model policy, then
            run an eval on that run to populate routing statistics.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Routing stats ({stats.length})</CardTitle>
          </CardHeader>
          <CardContent className="overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-1 pr-3">route key</th>
                  <th className="py-1 pr-3">node</th>
                  <th className="py-1 pr-3">model</th>
                  <th className="py-1 pr-3">pulls</th>
                  <th className="py-1 pr-3">avg reward</th>
                  <th className="py-1 pr-3">avg latency</th>
                  <th className="py-1 pr-3">avg cost</th>
                  <th className="py-1 pr-3">avg quality</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {stats.map((s) => (
                  <tr key={s.id} className="border-b border-border/50">
                    <td className="py-1 pr-3 text-muted-foreground">{s.route_key}</td>
                    <td className="py-1 pr-3">{s.node_id ?? "—"}</td>
                    <td className="py-1 pr-3 text-violet-400">{s.model_name}</td>
                    <td className="py-1 pr-3">{s.pulls}</td>
                    <td className="py-1 pr-3">{s.average_reward.toFixed(3)}</td>
                    <td className="py-1 pr-3">{Math.round(s.average_latency_ms)} ms</td>
                    <td className="py-1 pr-3">${s.average_cost_usd.toFixed(6)}</td>
                    <td className="py-1 pr-3">{s.average_quality_score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
