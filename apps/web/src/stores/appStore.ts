import { create } from "zustand";

import type { ServiceStatus } from "@/types";

interface AppState {
  backendStatus: ServiceStatus;
  dbStatus: ServiceStatus;
  setBackendStatus: (status: ServiceStatus) => void;
  setDbStatus: (status: ServiceStatus) => void;
}

export const useAppStore = create<AppState>((set) => ({
  backendStatus: "unknown",
  dbStatus: "unknown",
  setBackendStatus: (status) => set({ backendStatus: status }),
  setDbStatus: (status) => set({ dbStatus: status }),
}));
