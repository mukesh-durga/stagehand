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

// --- auth (Milestone 20) ---

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
}

export interface SigninPayload {
  email: string;
  password: string;
}

export * from "./workflow";
