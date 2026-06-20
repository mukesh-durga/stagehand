import { AlertCircle, ArrowLeft, Loader2, RefreshCw, Repeat } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ApiError, getRun, getRunReplays, getRunTrace, replayRun } from "@/lib/api";
import type { TraceEvent, WorkflowRun } from "@/types";

import { EvalSection } from "./EvalSection";
import { RunStatusBadge } from "./RunStatusBadge";
import { TraceEventDetail } from "./TraceEventDetail";

function eventBadgeVariant(eventType: string) {
  if (eventType.endsWith("_failed")) return "destructive" as const;
  if (eventType.endsWith("_completed")) return "success" as const;
  if (eventType === "retry_scheduled" || eventType === "fallback_used")
    return "muted" as const;
  return "default" as const;
}

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

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="max-h-64 overflow-auto rounded-md bg-background p-3 text-xs">
      {JSON.stringify(data ?? {}, null, 2)}
    </pre>
  );
}

const fmtTime = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [replays, setReplays] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [selected, setSelected] = useState<TraceEvent | null>(null);
  const [replaying, setReplaying] = useState(false);

  const load = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const [runData, traceData, replayData] = await Promise.all([
        getRun(runId),
        getRunTrace(runId),
        getRunReplays(runId),
      ]);
      setRun(runData);
      setEvents(traceData);
      setReplays(replayData);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
      } else {
        setError("Failed to load run.");
      }
    } finally {
      setLoading(false);
    }
  }, [runId]);

  const handleReplay = useCallback(async () => {
    if (!runId) return;
    setReplaying(true);
    try {
      const replay = await replayRun(runId);
      navigate(`/runs/${replay.id}`);
    } catch {
      setError("Failed to start replay.");
    } finally {
      setReplaying(false);
    }
  }, [runId, navigate]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading run…
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Button variant="ghost" className="w-fit" onClick={() => navigate("/runs")}>
          <ArrowLeft className="h-4 w-4" /> Runs
        </Button>
        <Card>
          <CardHeader>
            <CardTitle>Run not found</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            No run exists with id <code>{runId}</code>.
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        {error ?? "Failed to load run."}
        <Button size="sm" variant="outline" className="ml-3" onClick={() => void load()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button size="icon" variant="ghost" onClick={() => navigate("/runs")} title="Runs">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="font-mono text-sm text-muted-foreground">{run.id}</h1>
            <div className="mt-1 flex items-center gap-2">
              <RunStatusBadge status={run.status} />
              {run.replay_of_run_id && (
                <span className="text-xs text-muted-foreground">
                  replay of{" "}
                  <Link
                    to={`/runs/${run.replay_of_run_id}`}
                    className="font-mono underline hover:text-foreground"
                  >
                    {run.replay_of_run_id.slice(0, 8)}…
                  </Link>
                  {" · "}
                  <Link
                    to={`/runs/${run.replay_of_run_id}/diff/${run.id}`}
                    className="underline hover:text-foreground"
                  >
                    compare with original
                  </Link>
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => void handleReplay()} disabled={replaying}>
            {replaying ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Repeat className="h-3.5 w-3.5" />
            )}
            Replay run
          </Button>
          <Button size="sm" variant="outline" onClick={() => void load()}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        <MetricCard title="Status" value={<RunStatusBadge status={run.status} />} />
        <MetricCard
          title="Latency"
          value={run.total_latency_ms != null ? `${run.total_latency_ms} ms` : "—"}
        />
        <MetricCard title="Input tokens" value={run.total_input_tokens ?? "—"} />
        <MetricCard title="Output tokens" value={run.total_output_tokens ?? "—"} />
        <MetricCard
          title="Est. cost"
          value={
            run.estimated_cost_usd != null ? `$${run.estimated_cost_usd.toFixed(6)}` : "—"
          }
        />
        <MetricCard title="Started" value={<span className="text-xs">{fmtTime(run.started_at)}</span>} />
      </div>

      {/* Input / output / error */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Input</CardTitle>
          </CardHeader>
          <CardContent>
            <JsonBlock data={run.input} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>{run.status === "failed" ? "Error" : "Output"}</CardTitle>
          </CardHeader>
          <CardContent>
            {run.error_message ? (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                {run.error_message}
              </div>
            ) : (
              <JsonBlock data={run.output} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Evals */}
      <EvalSection runId={run.id} />

      {/* Trace timeline + detail */}
      <div className="flex flex-col gap-4 lg:flex-row">
        <Card className="min-w-0 flex-1">
          <CardHeader>
            <CardTitle>Trace timeline ({events.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <span className="text-sm text-muted-foreground">No trace events.</span>
            ) : (
              <ul className="flex flex-col gap-1 font-mono text-xs">
                {events.map((e) => (
                  <li key={e.event_id}>
                    <button
                      onClick={() => setSelected(e)}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-secondary",
                        selected?.event_id === e.event_id && "bg-secondary",
                      )}
                    >
                      <Badge variant={eventBadgeVariant(e.event_type)}>{e.event_type}</Badge>
                      {e.node_id && <span className="text-muted-foreground">{e.node_id}</span>}
                      {e.model_name && <span className="text-violet-400">{e.model_name}</span>}
                      {e.tool_name && <span className="text-amber-400">{e.tool_name}</span>}
                      {e.input_tokens + e.output_tokens > 0 && (
                        <span className="text-muted-foreground">
                          {e.input_tokens}/{e.output_tokens} tok
                        </span>
                      )}
                      {e.estimated_cost_usd > 0 && (
                        <span className="text-muted-foreground">
                          ${e.estimated_cost_usd.toFixed(4)}
                        </span>
                      )}
                      {e.latency_ms > 0 && (
                        <span className="text-muted-foreground">{e.latency_ms}ms</span>
                      )}
                      {e.error_message && (
                        <span className="truncate text-destructive">{e.error_message}</span>
                      )}
                      <span className="ml-auto shrink-0 text-muted-foreground">
                        {new Date(e.timestamp).toLocaleTimeString()}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {selected && (
          <TraceEventDetail event={selected} onClose={() => setSelected(null)} />
        )}
      </div>

      {/* Replays of this run */}
      {replays.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Replays ({replays.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex flex-col gap-2">
              {replays.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                >
                  <Link to={`/runs/${r.id}`} className="truncate font-mono text-xs hover:underline">
                    {r.id}
                  </Link>
                  <span className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">
                      {new Date(r.created_at).toLocaleString()}
                    </span>
                    <RunStatusBadge status={r.status} />
                    <Link
                      to={`/runs/${run.id}/diff/${r.id}`}
                      className="rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
                    >
                      Compare
                    </Link>
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
