import { create } from "zustand";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

interface BuilderState {
  selectedNodeId: string | null;
  workflowName: string;
  workflowDescription: string;
  saveStatus: SaveStatus;
  validationErrors: string[];

  setSelectedNodeId: (id: string | null) => void;
  setWorkflowName: (name: string) => void;
  setWorkflowDescription: (description: string) => void;
  setSaveStatus: (status: SaveStatus) => void;
  setValidationErrors: (errors: string[]) => void;
  reset: () => void;
}

const initial = {
  selectedNodeId: null,
  workflowName: "",
  workflowDescription: "",
  saveStatus: "idle" as SaveStatus,
  validationErrors: [] as string[],
};

export const useBuilderStore = create<BuilderState>((set) => ({
  ...initial,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  setWorkflowName: (workflowName) => set({ workflowName }),
  setWorkflowDescription: (workflowDescription) => set({ workflowDescription }),
  setSaveStatus: (saveStatus) => set({ saveStatus }),
  setValidationErrors: (validationErrors) => set({ validationErrors }),
  reset: () => set({ ...initial }),
}));
