/** Connection status used for backend/database health indicators. */
export type ServiceStatus = "unknown" | "checking" | "online" | "offline";

export interface HealthResponse {
  status: string;
}

export interface DbHealthResponse {
  status: string;
  database?: string;
  detail?: string;
}

export * from "./workflow";
