import "@xyflow/react/dist/style.css";

import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Connection,
  type NodeTypes,
} from "@xyflow/react";
import { AlertCircle, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  ApiError,
  createRun,
  createWorkflow,
  getWorkflow,
  updateWorkflow,
} from "@/lib/api";
import { connectRunTrace } from "@/lib/ws";
import { useBuilderStore } from "@/stores/builderStore";
import type {
  NodeRunStatus,
  TraceEvent,
  WorkflowNodeConfig,
  WorkflowNodeType,
} from "@/types";

import { BuilderTopBar } from "./BuilderTopBar";
import { CustomNode } from "./CustomNode";
import { fromWorkflowGraph, toWorkflowGraph, type BuilderEdge, type BuilderNode } from "./graph";
import { LiveTracePanel } from "./LiveTracePanel";
import { NODE_META } from "./nodeMeta";
import { NodeConfigPanel } from "./NodeConfigPanel";
import { NodeSidebar } from "./NodeSidebar";
import { validateWorkflow } from "./validation";

const nodeTypes: NodeTypes = {
  input: CustomNode,
  agent: CustomNode,
  tool: CustomNode,
  router: CustomNode,
  output: CustomNode,
};

export function BuilderPage() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();

  const [nodes, setNodes, onNodesChange] = useNodesState<BuilderNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<BuilderEdge>([]);
  const [loading, setLoading] = useState<boolean>(Boolean(workflowId));
  const [loadError, setLoadError] = useState<string | null>(null);

  const {
    workflowName,
    workflowDescription,
    selectedNodeId,
    setSelectedNodeId,
    setWorkflowName,
    setWorkflowDescription,
    setSaveStatus,
    setValidationErrors,
    reset,
  } = useBuilderStore();

  // Load existing workflow (or start empty for /workflows/new).
  useEffect(() => {
    reset();
    if (!workflowId) {
      setNodes([]);
      setEdges([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    getWorkflow(workflowId)
      .then((wf) => {
        setWorkflowName(wf.name);
        setWorkflowDescription(wf.description ?? "");
        const converted = fromWorkflowGraph(wf.graph);
        setNodes(converted.nodes);
        setEdges(converted.edges);
        setLoadError(null);
      })
      .catch((err) =>
        setLoadError(err instanceof Error ? err.message : "Failed to load workflow."),
      )
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId]);

  // --- live run / trace state ---
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string>("");
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  const setNodeRunStatus = useCallback(
    (nodeId: string, status: NodeRunStatus) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId ? { ...n, data: { ...n.data, runStatus: status } } : n,
        ),
      );
    },
    [setNodes],
  );

  const clearNodeRunStatuses = useCallback(() => {
    setNodes((nds) =>
      nds.map((n) => ({ ...n, data: { ...n.data, runStatus: undefined } })),
    );
  }, [setNodes]);

  const handleTraceEvent = useCallback(
    (event: TraceEvent) => {
      setTraceEvents((prev) => [...prev, event]);
      if (event.node_id) {
        if (event.event_type === "node_started") setNodeRunStatus(event.node_id, "running");
        else if (event.event_type === "node_completed")
          setNodeRunStatus(event.node_id, "completed");
        else if (event.event_type === "node_failed")
          setNodeRunStatus(event.node_id, "failed");
      }
      if (event.event_type === "run_completed") setRunStatus("completed");
      if (event.event_type === "run_failed") setRunStatus("failed");
    },
    [setNodeRunStatus],
  );

  const closeSocket = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
  }, []);

  // Close the socket when leaving the builder.
  useEffect(() => closeSocket, [closeSocket]);

  const handleRun = useCallback(async () => {
    if (!workflowId) return;
    closeSocket();
    setTraceEvents([]);
    clearNodeRunStatuses();
    setRunStatus("queued");
    try {
      const run = await createRun(workflowId, { query: "manual run from builder" });
      setRunId(run.id);
      setRunStatus(run.status);
      socketRef.current = connectRunTrace(run.id, { onEvent: handleTraceEvent });
    } catch (err) {
      setRunStatus("failed");
      setTraceEvents([]);
      setValidationErrors([
        err instanceof ApiError ? err.message : "Failed to start run.",
      ]);
    }
  }, [workflowId, closeSocket, clearNodeRunStatuses, handleTraceEvent, setValidationErrors]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge<BuilderEdge>(
          {
            ...connection,
            id: `edge-${crypto.randomUUID().slice(0, 8)}`,
            data: { condition: "" },
          } as BuilderEdge,
          eds,
        ),
      );
    },
    [setEdges],
  );

  const handleAddNode = useCallback(
    (type: WorkflowNodeType) => {
      const id = `${type}-${crypto.randomUUID().slice(0, 8)}`;
      setNodes((nds) => {
        const count = nds.length;
        const position = {
          x: 80 + (count % 4) * 210,
          y: 80 + Math.floor(count / 4) * 130,
        };
        const node: BuilderNode = {
          id,
          type,
          position,
          data: { config: NODE_META[type].defaultConfig() },
        };
        return [...nds, node];
      });
      setSelectedNodeId(id);
    },
    [setNodes, setSelectedNodeId],
  );

  const handleConfigChange = useCallback(
    (patch: Partial<WorkflowNodeConfig>) => {
      if (!selectedNodeId) return;
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNodeId
            ? { ...n, data: { ...n.data, config: { ...n.data.config, ...patch } } }
            : n,
        ),
      );
    },
    [selectedNodeId, setNodes],
  );

  const handleDeleteNode = useCallback(
    (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
      setSelectedNodeId(null);
    },
    [setNodes, setEdges, setSelectedNodeId],
  );

  const handleSave = useCallback(async () => {
    const graph = toWorkflowGraph(nodes, edges);
    const errors = validateWorkflow(workflowName, graph);
    if (errors.length > 0) {
      setValidationErrors(errors);
      setSaveStatus("idle");
      return;
    }
    setValidationErrors([]);
    setSaveStatus("saving");

    const payload = {
      name: workflowName,
      description: workflowDescription || null,
      graph,
    };

    try {
      if (workflowId) {
        await updateWorkflow(workflowId, payload);
        setSaveStatus("saved");
      } else {
        const created = await createWorkflow(payload);
        setSaveStatus("saved");
        navigate(`/workflows/${created.id}/builder`);
      }
    } catch (err) {
      setSaveStatus("error");
      const message =
        err instanceof ApiError ? err.message : "Failed to save workflow.";
      setValidationErrors([message]);
    }
  }, [
    nodes,
    edges,
    workflowName,
    workflowDescription,
    workflowId,
    navigate,
    setSaveStatus,
    setValidationErrors,
  ]);

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;

  return (
    <div className="flex h-full flex-col gap-3">
      <BuilderTopBar
        onSave={() => void handleSave()}
        onBack={() => navigate("/workflows")}
        onRun={() => void handleRun()}
        canRun={Boolean(workflowId)}
      />

      {loadError && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {loadError}
        </div>
      )}

      <div className="flex min-h-0 flex-1 gap-3">
        <NodeSidebar onAddNode={handleAddNode} />

        <div className="relative min-w-0 flex-1 overflow-hidden rounded-lg border border-border bg-card">
          {loading ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(null)}
              fitView
              colorMode="dark"
            >
              <Background />
              <Controls />
              <MiniMap pannable zoomable />
            </ReactFlow>
          )}
        </div>

        <NodeConfigPanel
          node={selectedNode}
          onChange={handleConfigChange}
          onDelete={handleDeleteNode}
        />
      </div>

      {runId && (
        <LiveTracePanel
          runId={runId}
          runStatus={runStatus}
          events={traceEvents}
          onClose={() => {
            closeSocket();
            setRunId(null);
          }}
        />
      )}
    </div>
  );
}
