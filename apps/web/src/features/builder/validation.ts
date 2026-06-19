import type { WorkflowGraph } from "@/types";

/**
 * Client-side validation mirroring the backend graph rules (Milestone 2).
 * The backend remains the source of truth; this gives fast inline feedback.
 */
export function validateWorkflow(name: string, graph: WorkflowGraph): string[] {
  const errors: string[] = [];

  if (!name.trim()) {
    errors.push("Workflow name is required.");
  }

  const { nodes, edges } = graph;

  if (nodes.length === 0) {
    errors.push("Graph must contain at least one node.");
    return errors;
  }

  const nodeIds = nodes.map((n) => n.id);
  if (new Set(nodeIds).size !== nodeIds.length) {
    errors.push("Node ids must be unique.");
  }

  const edgeIds = edges.map((e) => e.id);
  if (new Set(edgeIds).size !== edgeIds.length) {
    errors.push("Edge ids must be unique.");
  }

  const types = new Set(nodes.map((n) => n.type));
  if (!types.has("input")) {
    errors.push("Graph must contain at least one input node.");
  }
  if (!types.has("output")) {
    errors.push("Graph must contain at least one output node.");
  }

  const idSet = new Set(nodeIds);
  for (const edge of edges) {
    if (!idSet.has(edge.source)) {
      errors.push(`Edge '${edge.id}' source references a missing node.`);
    }
    if (!idSet.has(edge.target)) {
      errors.push(`Edge '${edge.id}' target references a missing node.`);
    }
  }

  if (nodes.length > 1 && edges.length === 0) {
    errors.push("Connect your nodes — a multi-node workflow needs at least one edge.");
  }

  return errors;
}
