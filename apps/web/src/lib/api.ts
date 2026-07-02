import type {
  AuthUser,
  BillingStatus,
  CheckoutSession,
  CloneTemplateRequest,
  DbHealthResponse,
  EvalRequest,
  EvalResult,
  HealthResponse,
  RoutingStat,
  RunDiffResponse,
  SigninPayload,
  SignupPayload,
  Template,
  TokenResponse,
  TraceEvent,
  UsageEvent,
  UsageSummary,
  Workflow,
  WorkflowCreatePayload,
  WorkflowRun,
  WorkflowUpdatePayload,
  WorkflowVersion,
} from "@/types";
import { getToken } from "@/lib/auth";

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
  const token = getToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string> | undefined) ?? {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
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

// --- auth ---

export function authSignup(payload: SignupPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function authSignin(payload: SigninPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/signin", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function authMe(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
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
): Promise<WorkflowRun> {
  return request<WorkflowRun>(`/workflows/${workflowId}/run`, {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}

export function getRun(runId: string): Promise<WorkflowRun> {
  return request<WorkflowRun>(`/runs/${runId}`);
}

export function getRunTrace(runId: string): Promise<TraceEvent[]> {
  return request<TraceEvent[]>(`/runs/${runId}/trace`);
}

export function listRuns(workflowId?: string): Promise<WorkflowRun[]> {
  const qs = workflowId ? `?workflow_id=${encodeURIComponent(workflowId)}` : "";
  return request<WorkflowRun[]>(`/runs${qs}`);
}

export function replayRun(runId: string): Promise<WorkflowRun> {
  return request<WorkflowRun>(`/runs/${runId}/replay`, { method: "POST" });
}

export function getRunReplays(runId: string): Promise<WorkflowRun[]> {
  return request<WorkflowRun[]>(`/runs/${runId}/replays`);
}

export function diffRuns(
  runId: string,
  otherRunId: string,
): Promise<RunDiffResponse> {
  return request<RunDiffResponse>(`/runs/${runId}/diff/${otherRunId}`);
}

// --- evals ---

export function runEval(runId: string, payload: EvalRequest): Promise<EvalResult[]> {
  return request<EvalResult[]>(`/runs/${runId}/eval`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getRunEvals(runId: string): Promise<EvalResult[]> {
  return request<EvalResult[]>(`/runs/${runId}/evals`);
}

// --- routing ---

export function getRoutingStats(): Promise<RoutingStat[]> {
  return request<RoutingStat[]>("/routing/stats");
}

// --- templates ---

export function listTemplates(): Promise<Template[]> {
  return request<Template[]>("/templates");
}

export function getTemplate(slug: string): Promise<Template> {
  return request<Template>(`/templates/${slug}`);
}

export function cloneTemplate(
  slug: string,
  payload: CloneTemplateRequest = {},
): Promise<Workflow> {
  return request<Workflow>(`/templates/${slug}/clone`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- usage & billing ---

export function getUsageEvents(): Promise<UsageEvent[]> {
  return request<UsageEvent[]>("/usage/events");
}

export function getUsageSummary(): Promise<UsageSummary> {
  return request<UsageSummary>("/usage/summary");
}

export function backfillUsage(): Promise<{ inserted: number }> {
  return request<{ inserted: number }>("/usage/backfill", { method: "POST" });
}

export function getBillingStatus(): Promise<BillingStatus> {
  return request<BillingStatus>("/billing/status");
}

export function createCheckoutSession(): Promise<CheckoutSession> {
  return request<CheckoutSession>("/billing/create-checkout-session", {
    method: "POST",
  });
}
