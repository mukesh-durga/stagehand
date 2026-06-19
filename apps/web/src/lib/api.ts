import type {
  DbHealthResponse,
  HealthResponse,
  Workflow,
  WorkflowCreatePayload,
  WorkflowRunResponse,
  WorkflowUpdatePayload,
  WorkflowVersion,
} from "@/types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Error carrying the HTTP status and the backend's `detail` message. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the backend API.");
  }

  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((d: { msg?: string }) => d.msg ?? JSON.stringify(d))
          .join("; ");
      }
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail ?? `Request failed (${res.status})`);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

// --- health ---

export function healthCheck(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function dbHealthCheck(): Promise<DbHealthResponse> {
  return request<DbHealthResponse>("/health/db");
}

// --- workflows ---

export function listWorkflows(): Promise<Workflow[]> {
  return request<Workflow[]>("/workflows");
}

export function getWorkflow(id: string): Promise<Workflow> {
  return request<Workflow>(`/workflows/${id}`);
}

export function createWorkflow(payload: WorkflowCreatePayload): Promise<Workflow> {
  return request<Workflow>("/workflows", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateWorkflow(
  id: string,
  payload: WorkflowUpdatePayload,
): Promise<Workflow> {
  return request<Workflow>(`/workflows/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteWorkflow(id: string): Promise<void> {
  return request<void>(`/workflows/${id}`, { method: "DELETE" });
}

export function getWorkflowVersions(id: string): Promise<WorkflowVersion[]> {
  return request<WorkflowVersion[]>(`/workflows/${id}/versions`);
}

// --- runs ---

export function createRun(
  workflowId: string,
  input: Record<string, unknown>,
): Promise<WorkflowRunResponse> {
  return request<WorkflowRunResponse>(`/workflows/${workflowId}/run`, {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}
