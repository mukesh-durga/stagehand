/**
 * Frontend-only auth flag.
 *
 * This is NOT real authentication — there is no backend, session, or token. It
 * only records that the visitor "signed in" so app routes can be gated and the
 * public site stays separate. localStorage access is guarded so private-mode or
 * SSR quirks never crash the app.
 */
export const AUTH_KEY = "stagehand_auth";

export function isAuthed(): boolean {
  try {
    return localStorage.getItem(AUTH_KEY) === "true";
  } catch {
    return false;
  }
}

export function signIn(): void {
  try {
    localStorage.setItem(AUTH_KEY, "true");
  } catch {
    // Ignore storage failures — signing in must never block navigation.
  }
}

export function signOut(): void {
  try {
    localStorage.removeItem(AUTH_KEY);
  } catch {
    // Ignore storage failures — signing out must never block navigation.
  }
}
