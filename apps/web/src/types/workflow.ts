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
  fallbackModel?: string;
  // mock-only failure triggers (for testing retry/fallback)
  failTimes?: number;
  forceFailure?: boolean;
  // tool
  toolName?: string;
  expression?: string;
  query?: string;
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

export interface WorkflowRun {
  id: string;
  workflow_id: string;
  workflow_version_id: string;
  status: string;
  replay_of_run_id: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error_message: string | null;
  total_latency_ms: number | null;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
  estimated_cost_usd: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

/** Backwards-compatible alias (the run-create endpoint returns the full run). */
export type WorkflowRunResponse = WorkflowRun;

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

// --- run diff (Milestone 13) ---

export interface RunDiffSummary {
  status_changed: boolean;
  workflow_version_changed: boolean;
  latency_delta_ms: number;
  input_tokens_delta: number;
  output_tokens_delta: number;
  cost_delta: number;
  error_changed: boolean;
  model_changed: boolean;
  tool_changed: boolean;
  retry_count_delta: number;
  fallback_changed: boolean;
}

export interface NodeDiff {
  node_id: string;
  status_a: string;
  status_b: string;
  status_changed: boolean;
  model_a: string;
  model_b: string;
  model_changed: boolean;
  tool_a: string;
  tool_b: string;
  tool_changed: boolean;
  latency_a_ms: number;
  latency_b_ms: number;
  latency_delta_ms: number;
  input_tokens_a: number;
  input_tokens_b: number;
  output_tokens_a: number;
  output_tokens_b: number;
  cost_a: number;
  cost_b: number;
  cost_delta: number;
  retry_count_a: number;
  retry_count_b: number;
  fallback_used_a: boolean;
  fallback_used_b: boolean;
  error_a: string;
  error_b: string;
  output_summary_a: string;
  output_summary_b: string;
}

export interface EventDiff {
  event_type: string;
  node_id: string;
  count_a: number;
  count_b: number;
  changed: boolean;
  details: string;
}

export interface OutputDiff {
  changed: boolean;
  output_a_summary: string;
  output_b_summary: string;
}

export interface RunDiffResponse {
  run_a: WorkflowRun;
  run_b: WorkflowRun;
  summary: RunDiffSummary;
  node_diffs: NodeDiff[];
  event_diffs: EventDiff[];
  output_diff: OutputDiff;
}

// --- eval harness (Milestone 14) ---

export interface EvalRequest {
  eval_types?: string[];
  expected_output?: unknown;
  expected_schema?: Record<string, unknown>;
  expected_tools?: string[];
  max_latency_ms?: number;
  max_cost_usd?: number;
  judge_prompt?: string;
}

export interface EvalResult {
  id: string;
  run_id: string;
  workflow_id: string;
  workflow_version_id: string;
  eval_type: string;
  success_score: number;
  tool_correctness_score: number | null;
  format_score: number | null;
  quality_score: number | null;
  cost_score: number | null;
  latency_score: number | null;
  passed: boolean;
  feedback: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}
