/** Workflow domain types, aligned with the backend Pydantic schemas (Milestone 2). */

export type WorkflowNodeType = "input" | "agent" | "tool" | "router" | "output";

export type ModelPolicy = "cheap" | "strong" | "adaptive";

export interface WorkflowNodeConfig {
  label: string;
  // agent
  prompt?: string;
  modelPolicy?: ModelPolicy;
  allowedTools?: string[];
  maxRetries?: number;
  timeoutMs?: number;
  maxCostUsd?: number;
  // tool
  toolName?: string;
  // router
  condition?: string;
  // input / output
  inputKey?: string;
  outputKey?: string;
  // backend stores config as an arbitrary object
  [key: string]: unknown;
}

export interface WorkflowNode {
  id: string;
  type: WorkflowNodeType;
  position: { x: number; y: number };
  config: WorkflowNodeConfig;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string | null;
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  current_version_id: string | null;
  current_version_number: number | null;
  graph: WorkflowGraph;
  created_at: string;
  updated_at: string;
}

export interface WorkflowVersion {
  id: string;
  workflow_id: string;
  version_number: number;
  graph: WorkflowGraph;
  created_at: string;
}

export interface WorkflowCreatePayload {
  name: string;
  description?: string | null;
  graph: WorkflowGraph;
}

export interface WorkflowUpdatePayload {
  name?: string;
  description?: string | null;
  graph?: WorkflowGraph;
}

export interface WorkflowRunResponse {
  id: string;
  workflow_id: string;
  workflow_version_id: string;
  status: string;
}

export type NodeRunStatus = "running" | "completed" | "failed";

export interface TraceEvent {
  event_id: string;
  run_id: string;
  workflow_id: string;
  workflow_version_id: string;
  node_id: string;
  event_type: string;
  status: string;
  timestamp: string;
  latency_ms: number;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  tool_name: string;
  retry_count: number;
  error_message: string;
  metadata_json: Record<string, unknown>;
}
