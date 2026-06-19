import type { Edge, Node } from "@xyflow/react";

import type {
  NodeRunStatus,
  WorkflowEdge,
  WorkflowGraph,
  WorkflowNodeConfig,
  WorkflowNodeType,
} from "@/types";

/** Data carried on a React Flow node in the builder. */
export interface BuilderNodeData extends Record<string, unknown> {
  config: WorkflowNodeConfig;
  /** Live execution status from trace events (UI-only, not persisted). */
  runStatus?: NodeRunStatus;
}

export type BuilderNode = Node<BuilderNodeData>;
export type BuilderEdge = Edge<{ condition?: string }>;

/** Convert React Flow state into the backend WorkflowGraph shape. */
export function toWorkflowGraph(
  nodes: BuilderNode[],
  edges: BuilderEdge[],
): WorkflowGraph {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type as WorkflowNodeType,
      position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
      config: n.data.config,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      condition: e.data?.condition ?? null,
    })),
  };
}

/** Convert a backend WorkflowGraph into React Flow nodes and edges. */
export function fromWorkflowGraph(graph: WorkflowGraph): {
  nodes: BuilderNode[];
  edges: BuilderEdge[];
} {
  return {
    nodes: graph.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: { config: n.config },
    })),
    edges: graph.edges.map((e: WorkflowEdge) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      data: { condition: e.condition ?? undefined },
    })),
  };
}
