/**
 * Frontend-only "demo entered" flag.
 *
 * This is NOT authentication — it just remembers that the visitor clicked
 * "Enter Demo" so we can land them on the dashboard next time. No backend call,
 * no session, no security. localStorage access is guarded so SSR/incognito
 * quirks never crash the app.
 */
export const DEMO_ENTERED_KEY = "stagehand_demo_entered";

export function hasEnteredDemo(): boolean {
  try {
    return localStorage.getItem(DEMO_ENTERED_KEY) === "true";
  } catch {
    return false;
  }
}

export function enterDemo(): void {
  try {
    localStorage.setItem(DEMO_ENTERED_KEY, "true");
  } catch {
    // Ignore storage failures — entering the demo must never block navigation.
  }
}
