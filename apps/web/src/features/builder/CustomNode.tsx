import { Handle, Position, type NodeProps } from "@xyflow/react";

import { cn } from "@/lib/utils";
import type { WorkflowNodeType } from "@/types";

import { NODE_META } from "./nodeMeta";
import type { BuilderNode } from "./graph";

export function CustomNode({ type, data, selected }: NodeProps<BuilderNode>) {
  const nodeType = type as WorkflowNodeType;
  const meta = NODE_META[nodeType];
  const Icon = meta.icon;
  const label = data.config.label || meta.label;

  const showTarget = nodeType !== "input";
  const showSource = nodeType !== "output";

  return (
    <div
      className={cn(
        "min-w-[160px] rounded-md border border-l-4 bg-card px-3 py-2 shadow-sm",
        meta.accent,
        selected ? "ring-2 ring-ring" : "border-border",
      )}
    >
      {showTarget && (
        <Handle type="target" position={Position.Left} className="!h-2 !w-2 !bg-muted-foreground" />
      )}

      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4", meta.accent.split(" ").pop())} />
        <div className="flex flex-col">
          <span className="text-sm font-medium leading-tight text-card-foreground">
            {label}
          </span>
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {meta.label}
          </span>
        </div>
        {data.runStatus && (
          <span
            className={cn(
              "ml-auto rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase",
              data.runStatus === "running" && "bg-primary/20 text-primary",
              data.runStatus === "completed" && "bg-success/20 text-success",
              data.runStatus === "failed" && "bg-destructive/20 text-destructive",
            )}
          >
            {data.runStatus}
          </span>
        )}
      </div>

      {showSource && (
        <Handle type="source" position={Position.Right} className="!h-2 !w-2 !bg-muted-foreground" />
      )}
    </div>
  );
}
