/**
 * Client-side auth session backed by a real backend JWT.
 *
 * The token is issued by the API (/auth/signup, /auth/signin) and stored in
 * localStorage. Route guards use token presence; API requests attach it as a
 * Bearer header. localStorage access is guarded so private-mode/SSR never crash.
 */
import type { AuthUser } from "@/types";

export const TOKEN_KEY = "stagehand_access_token";
export const USER_KEY = "stagehand_user";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getCurrentUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: AuthUser): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // Ignore storage failures — a failed write must never block navigation.
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // Ignore storage failures.
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}
