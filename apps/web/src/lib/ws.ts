import { API_BASE_URL } from "@/lib/api";
import type { TraceEvent } from "@/types";

/**
 * Base ws(s):// URL for trace streams.
 *
 * Prefers VITE_WS_BASE_URL (set this in production when the WS origin differs
 * from the HTTP API, e.g. behind a proxy). Otherwise it is derived from
 * VITE_API_BASE_URL by swapping the http(s) scheme for ws(s) — so https:// API
 * URLs correctly yield wss:// in production while local http stays ws.
 */
export const WS_BASE_URL =
  (import.meta.env.VITE_WS_BASE_URL as string | undefined) ??
  API_BASE_URL.replace(/^http/, "ws");

/** Build the ws(s):// URL for a run's trace stream. */
export function runTraceSocketUrl(runId: string): string {
  const base = WS_BASE_URL.replace(/\/+$/, "");
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
