import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { TraceEvent } from "@/types";

interface TraceEventDetailProps {
  event: TraceEvent;
  onClose: () => void;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === "" || value === null || value === undefined) return null;
  return (
    <div className="flex justify-between gap-3 py-1 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="break-all text-right font-mono">{value}</span>
    </div>
  );
}

export function TraceEventDetail({ event, onClose }: TraceEventDetailProps) {
  return (
    <aside className="flex w-80 shrink-0 flex-col gap-2 overflow-auto rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{event.event_type}</span>
        <Button size="icon" variant="ghost" onClick={onClose} title="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex flex-col divide-y divide-border">
        <Row label="event_id" value={event.event_id} />
        <Row label="node_id" value={event.node_id} />
        <Row label="status" value={event.status} />
        <Row label="timestamp" value={new Date(event.timestamp).toLocaleString()} />
        <Row label="latency_ms" value={event.latency_ms || ""} />
        <Row label="model_name" value={event.model_name} />
        <Row label="tool_name" value={event.tool_name} />
        <Row label="input_tokens" value={event.input_tokens || ""} />
        <Row label="output_tokens" value={event.output_tokens || ""} />
        <Row
          label="estimated_cost_usd"
          value={event.estimated_cost_usd ? `$${event.estimated_cost_usd.toFixed(6)}` : ""}
        />
        <Row label="retry_count" value={event.retry_count || ""} />
        <Row label="error_message" value={event.error_message} />
      </div>

      <div className="mt-2">
        <span className="text-xs text-muted-foreground">metadata_json</span>
        <pre className="mt-1 overflow-auto rounded-md bg-background p-2 text-[11px]">
          {JSON.stringify(event.metadata_json ?? {}, null, 2)}
        </pre>
      </div>
    </aside>
  );
}
