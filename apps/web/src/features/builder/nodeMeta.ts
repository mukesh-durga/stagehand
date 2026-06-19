import {
  Bot,
  GitBranch,
  LogIn,
  LogOut,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import type { WorkflowNodeConfig, WorkflowNodeType } from "@/types";

interface NodeMeta {
  type: WorkflowNodeType;
  label: string;
  icon: LucideIcon;
  /** Tailwind classes for the node's accent (border + icon color). */
  accent: string;
  defaultConfig: () => WorkflowNodeConfig;
}

export const NODE_META: Record<WorkflowNodeType, NodeMeta> = {
  input: {
    type: "input",
    label: "Input",
    icon: LogIn,
    accent: "border-l-sky-500 text-sky-400",
    defaultConfig: () => ({ label: "Input", inputKey: "" }),
  },
  agent: {
    type: "agent",
    label: "Agent",
    icon: Bot,
    accent: "border-l-violet-500 text-violet-400",
    defaultConfig: () => ({
      label: "Agent",
      prompt: "",
      modelPolicy: "adaptive",
      allowedTools: [],
      maxRetries: 2,
      timeoutMs: 30000,
      maxCostUsd: 0.1,
    }),
  },
  tool: {
    type: "tool",
    label: "Tool",
    icon: Wrench,
    accent: "border-l-amber-500 text-amber-400",
    defaultConfig: () => ({
      label: "Tool",
      toolName: "",
      timeoutMs: 15000,
      maxRetries: 1,
    }),
  },
  router: {
    type: "router",
    label: "Router",
    icon: GitBranch,
    accent: "border-l-pink-500 text-pink-400",
    defaultConfig: () => ({ label: "Router", condition: "" }),
  },
  output: {
    type: "output",
    label: "Output",
    icon: LogOut,
    accent: "border-l-emerald-500 text-emerald-400",
    defaultConfig: () => ({ label: "Output", outputKey: "" }),
  },
};

export const NODE_TYPES_ORDER: WorkflowNodeType[] = [
  "input",
  "agent",
  "tool",
  "router",
  "output",
];
