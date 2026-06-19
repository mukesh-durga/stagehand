import { API_BASE_URL } from "@/lib/api";
import type { TraceEvent } from "@/types";

/** Build the ws(s):// URL for a run's trace stream from the HTTP API base. */
export function runTraceSocketUrl(runId: string): string {
  const base = API_BASE_URL.replace(/^http/, "ws");
  return `${base}/ws/runs/${runId}`;
}

export interface TraceSocketHandlers {
  onEvent: (event: TraceEvent) => void;
  onOpen?: () => void;
  onError?: (event: Event) => void;
  onClose?: () => void;
}

/**
 * Connect to a run's live trace WebSocket. The server sends a `{type:"connected"}`
 * system message first, then `TraceEvent` objects. Returns the socket so callers
 * can close it.
 */
export function connectRunTrace(
  runId: string,
  handlers: TraceSocketHandlers,
): WebSocket {
  const socket = new WebSocket(runTraceSocketUrl(runId));

  socket.onopen = () => handlers.onOpen?.();
  socket.onerror = (event) => handlers.onError?.(event);
  socket.onclose = () => handlers.onClose?.();
  socket.onmessage = (message) => {
    let data: unknown;
    try {
      data = JSON.parse(message.data);
    } catch {
      return;
    }
    if (data && typeof data === "object" && "type" in data) {
      // System messages ({type:"connected"} / {type:"error"}) — ignore for now.
      return;
    }
    handlers.onEvent(data as TraceEvent);
  };

  return socket;
}
