import { Plus } from "lucide-react";

import { cn } from "@/lib/utils";
import type { WorkflowNodeType } from "@/types";

import { NODE_META, NODE_TYPES_ORDER } from "./nodeMeta";

interface NodeSidebarProps {
  onAddNode: (type: WorkflowNodeType) => void;
}

export function NodeSidebar({ onAddNode }: NodeSidebarProps) {
  return (
    <aside className="flex w-48 shrink-0 flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <span className="px-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Add node
      </span>
      {NODE_TYPES_ORDER.map((type) => {
        const meta = NODE_META[type];
        const Icon = meta.icon;
        return (
          <button
            key={type}
            onClick={() => onAddNode(type)}
            className={cn(
              "flex items-center gap-2 rounded-md border border-l-4 border-border bg-background px-3 py-2 text-sm",
              "transition-colors hover:bg-secondary",
              meta.accent,
            )}
          >
            <Icon className={cn("h-4 w-4", meta.accent.split(" ").pop())} />
            <span className="text-foreground">{meta.label}</span>
            <Plus className="ml-auto h-3.5 w-3.5 text-muted-foreground" />
          </button>
        );
      })}
    </aside>
  );
}
