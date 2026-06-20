import { AlertCircle, AlertTriangle, ArrowLeft, Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ApiError, diffRuns } from "@/lib/api";
import type { RunDiffResponse } from "@/types";

import { RunStatusBadge } from "./RunStatusBadge";

function ChangeCard({
  title,
  value,
  changed,
}: {
  title: string;
  value: React.ReactNode;
  changed: boolean;
}) {
  return (
    <Card className={cn(changed && "border-primary/60")}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="text-lg font-semibold text-foreground">{value}</span>
      </CardHeader>
    </Card>
  );
}

const delta = (n: number) => (n > 0 ? `+${n}` : `${n}`);
const yesNo = (b: boolean) => (b ? "changed" : "same");

export function RunDiffPage() {
  const { runId, otherRunId } = useParams<{ runId: string; otherRunId: string }>();
  const navigate = useNavigate();

  const [diff, setDiff] = useState<RunDiffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    if (!runId || !otherRunId) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      setDiff(await diffRuns(runId, otherRunId));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
      else setError("Failed to load diff.");
    } finally {
      setLoading(false);
    }
  }, [runId, otherRunId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading diff…
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" /> One or both runs were not found.
      </div>
    );
  }

  if (error || !diff) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        {error ?? "Failed to load diff."}
        <Button size="sm" variant="outline" className="ml-3" onClick={() => void load()}>
          Retry
        </Button>
      </div>
    );
  }

  const { run_a, run_b, summary, node_diffs, event_diffs, output_diff } = diff;
  const anyDiff =
    summary.status_changed ||
    summary.latency_delta_ms !== 0 ||
    summary.input_tokens_delta !== 0 ||
    summary.output_tokens_delta !== 0 ||
    summary.cost_delta !== 0 ||
    summary.error_changed ||
    summary.model_changed ||
    summary.tool_changed ||
    summary.retry_count_delta !== 0 ||
    summary.fallback_changed ||
    output_diff.changed;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button size="icon" variant="ghost" onClick={() => navigate(`/runs/${runId}`)} title="Back">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex flex-1 items-center gap-6 text-sm">
          <div>
            <div className="text-xs text-muted-foreground">Run A</div>
            <button onClick={() => navigate(`/runs/${run_a.id}`)} className="font-mono hover:underline">
              {run_a.id.slice(0, 8)}…
            </button>{" "}
            <RunStatusBadge status={run_a.status} />
          </div>
          <span className="text-muted-foreground">vs</span>
          <div>
            <div className="text-xs text-muted-foreground">Run B</div>
            <button onClick={() => navigate(`/runs/${run_b.id}`)} className="font-mono hover:underline">
              {run_b.id.slice(0, 8)}…
            </button>{" "}
            <RunStatusBadge status={run_b.status} />
          </div>
        </div>
      </div>

      {summary.workflow_version_changed && (
        <div className="flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-400">
          <AlertTriangle className="h-4 w-4" /> These runs used different workflow versions.
        </div>
      )}

      {!anyDiff && (
        <div className="rounded-md border border-success/40 bg-success/10 px-3 py-2 text-sm text-success">
          No differences detected between these runs.
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
        <ChangeCard title="Status" value={yesNo(summary.status_changed)} changed={summary.status_changed} />
        <ChangeCard
          title="Latency Δ"
          value={`${delta(summary.latency_delta_ms)} ms`}
          changed={summary.latency_delta_ms !== 0}
        />
        <ChangeCard
          title="Output tok Δ"
          value={delta(summary.output_tokens_delta)}
          changed={summary.output_tokens_delta !== 0}
        />
        <ChangeCard
          title="Cost Δ"
          value={`$${summary.cost_delta.toFixed(6)}`}
          changed={summary.cost_delta !== 0}
        />
        <ChangeCard title="Retries Δ" value={delta(summary.retry_count_delta)} changed={summary.retry_count_delta !== 0} />
        <ChangeCard title="Fallback" value={yesNo(summary.fallback_changed)} changed={summary.fallback_changed} />
        <ChangeCard title="Model/Tool" value={yesNo(summary.model_changed || summary.tool_changed)} changed={summary.model_changed || summary.tool_changed} />
      </div>

      {/* Node diff table */}
      <Card>
        <CardHeader>
          <CardTitle>Node comparison ({node_diffs.length})</CardTitle>
        </CardHeader>
        <CardContent className="overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border">
                <th className="py-1 pr-3">node</th>
                <th className="py-1 pr-3">status A/B</th>
                <th className="py-1 pr-3">model A/B</th>
                <th className="py-1 pr-3">tool A/B</th>
                <th className="py-1 pr-3">latency Δ</th>
                <th className="py-1 pr-3">out tok A/B</th>
                <th className="py-1 pr-3">cost Δ</th>
                <th className="py-1 pr-3">retries A/B</th>
                <th className="py-1 pr-3">fallback</th>
                <th className="py-1 pr-3">error</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {node_diffs.map((n) => (
                <tr key={n.node_id} className="border-b border-border/50">
                  <td className="py-1 pr-3">{n.node_id}</td>
                  <td className={cn("py-1 pr-3", n.status_changed && "text-primary")}>
                    {n.status_a || "—"} / {n.status_b || "—"}
                  </td>
                  <td className={cn("py-1 pr-3", n.model_changed && "text-primary")}>
                    {n.model_a || "—"} / {n.model_b || "—"}
                  </td>
                  <td className={cn("py-1 pr-3", n.tool_changed && "text-primary")}>
                    {n.tool_a || "—"} / {n.tool_b || "—"}
                  </td>
                  <td className={cn("py-1 pr-3", n.latency_delta_ms !== 0 && "text-primary")}>
                    {delta(n.latency_delta_ms)} ms
                  </td>
                  <td className="py-1 pr-3">
                    {n.output_tokens_a} / {n.output_tokens_b}
                  </td>
                  <td className={cn("py-1 pr-3", n.cost_delta !== 0 && "text-primary")}>
                    ${n.cost_delta.toFixed(6)}
                  </td>
                  <td className="py-1 pr-3">
                    {n.retry_count_a} / {n.retry_count_b}
                  </td>
                  <td className="py-1 pr-3">
                    {String(n.fallback_used_a)} / {String(n.fallback_used_b)}
                  </td>
                  <td className="py-1 pr-3 text-destructive">
                    {n.error_a || n.error_b ? `${n.error_a || "—"} / ${n.error_b || "—"}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Event diff */}
      <Card>
        <CardHeader>
          <CardTitle>Event differences</CardTitle>
        </CardHeader>
        <CardContent className="overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-muted-foreground">
              <tr className="border-b border-border">
                <th className="py-1 pr-3">event type</th>
                <th className="py-1 pr-3">node</th>
                <th className="py-1 pr-3">count A</th>
                <th className="py-1 pr-3">count B</th>
                <th className="py-1 pr-3">changed</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {event_diffs.map((e) => (
                <tr
                  key={`${e.event_type}:${e.node_id}`}
                  className={cn("border-b border-border/50", e.changed && "text-primary")}
                >
                  <td className="py-1 pr-3">{e.event_type}</td>
                  <td className="py-1 pr-3">{e.node_id || "—"}</td>
                  <td className="py-1 pr-3">{e.count_a}</td>
                  <td className="py-1 pr-3">{e.count_b}</td>
                  <td className="py-1 pr-3">{e.changed ? "yes" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Output diff */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Output</CardTitle>
          <Badge variant={output_diff.changed ? "destructive" : "success"}>
            {output_diff.changed ? "changed" : "unchanged"}
          </Badge>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div>
            <div className="mb-1 text-xs text-muted-foreground">Run A</div>
            <pre className="max-h-56 overflow-auto rounded-md bg-background p-3 text-xs">
              {output_diff.output_a_summary}
            </pre>
          </div>
          <div>
            <div className="mb-1 text-xs text-muted-foreground">Run B</div>
            <pre className="max-h-56 overflow-auto rounded-md bg-background p-3 text-xs">
              {output_diff.output_b_summary}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
