import { ExternalLink, X } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/types";

interface LiveTracePanelProps {
  runId: string;
  runStatus: string;
  events: TraceEvent[];
  onClose: () => void;
}

function eventBadgeVariant(eventType: string) {
  if (eventType.endsWith("_failed")) return "destructive" as const;
  if (eventType.endsWith("_completed")) return "success" as const;
  if (eventType === "retry_scheduled" || eventType === "fallback_used")
    return "muted" as const;
  return "default" as const;
}

export function LiveTracePanel({ runId, runStatus, events, onClose }: LiveTracePanelProps) {
  return (
    <div className="flex h-56 shrink-0 flex-col rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-3 text-sm">
          <span className="font-medium">Live run</span>
          <code className="text-xs text-muted-foreground">{runId}</code>
          <Badge
            variant={
              runStatus === "completed"
                ? "success"
                : runStatus === "failed"
                  ? "destructive"
                  : "default"
            }
          >
            {runStatus}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/runs/${runId}`}
            className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Open run details
          </Link>
          <Button size="icon" variant="ghost" onClick={onClose} title="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 font-mono text-xs">
        {events.length === 0 ? (
          <span className="text-muted-foreground">Waiting for events…</span>
        ) : (
          <ul className="flex flex-col gap-1">
            {events.map((e) => (
              <li key={e.event_id} className="flex items-center gap-2">
                <Badge variant={eventBadgeVariant(e.event_type)}>{e.event_type}</Badge>
                {e.node_id && <span className="text-muted-foreground">{e.node_id}</span>}
                {e.model_name && <span className="text-violet-400">{e.model_name}</span>}
                {e.tool_name && <span className="text-amber-400">{e.tool_name}</span>}
                {typeof e.metadata_json?.attempt === "number" && (
                  <span className="text-muted-foreground">
                    attempt {e.metadata_json.attempt}
                  </span>
                )}
                <span
                  className={cn(
                    e.status === "success" && "text-success",
                    e.status === "failed" && "text-destructive",
                  )}
                >
                  {e.status}
                </span>
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
                  <span className="text-destructive">{e.error_message}</span>
                )}
                <span className="ml-auto text-muted-foreground">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
