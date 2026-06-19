import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { ModelPolicy, WorkflowNodeConfig } from "@/types";

import type { BuilderNode } from "./graph";
import { NODE_META } from "./nodeMeta";

interface NodeConfigPanelProps {
  node: BuilderNode | null;
  onChange: (patch: Partial<WorkflowNodeConfig>) => void;
  onDelete: (id: string) => void;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

export function NodeConfigPanel({ node, onChange, onDelete }: NodeConfigPanelProps) {
  if (!node) {
    return (
      <aside className="flex w-72 shrink-0 flex-col rounded-lg border border-border bg-card p-4">
        <span className="text-sm text-muted-foreground">
          Select a node to edit its configuration.
        </span>
      </aside>
    );
  }

  const type = node.type as keyof typeof NODE_META;
  const config = node.data.config;
  const meta = NODE_META[type];

  const num = (v: string): number | undefined =>
    v === "" ? undefined : Number(v);

  return (
    <aside className="flex w-72 shrink-0 flex-col gap-4 overflow-auto rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{meta.label} node</span>
        <Button size="icon" variant="ghost" onClick={() => onDelete(node.id)} title="Delete node">
          <Trash2 className="h-4 w-4 text-destructive" />
        </Button>
      </div>

      <Field label="Label">
        <Input
          value={config.label ?? ""}
          onChange={(e) => onChange({ label: e.target.value })}
        />
      </Field>

      {type === "input" && (
        <Field label="Input key (optional)">
          <Input
            value={config.inputKey ?? ""}
            onChange={(e) => onChange({ inputKey: e.target.value })}
            placeholder="query"
          />
        </Field>
      )}

      {type === "output" && (
        <Field label="Output key (optional)">
          <Input
            value={config.outputKey ?? ""}
            onChange={(e) => onChange({ outputKey: e.target.value })}
            placeholder="result"
          />
        </Field>
      )}

      {type === "agent" && (
        <>
          <Field label="Prompt">
            <Textarea
              value={config.prompt ?? ""}
              onChange={(e) => onChange({ prompt: e.target.value })}
              placeholder="You are a helpful agent…"
            />
          </Field>
          <Field label="Model policy">
            <Select
              value={config.modelPolicy ?? "adaptive"}
              onChange={(e) => onChange({ modelPolicy: e.target.value as ModelPolicy })}
            >
              <option value="cheap">cheap</option>
              <option value="strong">strong</option>
              <option value="adaptive">adaptive</option>
            </Select>
          </Field>
          <Field label="Allowed tools (comma-separated)">
            <Input
              value={(config.allowedTools ?? []).join(", ")}
              onChange={(e) =>
                onChange({
                  allowedTools: e.target.value
                    .split(",")
                    .map((t) => t.trim())
                    .filter(Boolean),
                })
              }
              placeholder="calculator, mock_search"
            />
          </Field>
          <Field label="Max retries">
            <Input
              type="number"
              value={config.maxRetries ?? ""}
              onChange={(e) => onChange({ maxRetries: num(e.target.value) })}
            />
          </Field>
          <Field label="Timeout (ms)">
            <Input
              type="number"
              value={config.timeoutMs ?? ""}
              onChange={(e) => onChange({ timeoutMs: num(e.target.value) })}
            />
          </Field>
          <Field label="Max cost (USD)">
            <Input
              type="number"
              step="0.01"
              value={config.maxCostUsd ?? ""}
              onChange={(e) => onChange({ maxCostUsd: num(e.target.value) })}
            />
          </Field>
        </>
      )}

      {type === "tool" && (
        <>
          <Field label="Tool name">
            <Input
              value={config.toolName ?? ""}
              onChange={(e) => onChange({ toolName: e.target.value })}
              placeholder="calculator"
            />
          </Field>
          <Field label="Timeout (ms)">
            <Input
              type="number"
              value={config.timeoutMs ?? ""}
              onChange={(e) => onChange({ timeoutMs: num(e.target.value) })}
            />
          </Field>
          <Field label="Max retries">
            <Input
              type="number"
              value={config.maxRetries ?? ""}
              onChange={(e) => onChange({ maxRetries: num(e.target.value) })}
            />
          </Field>
        </>
      )}

      {type === "router" && (
        <Field label="Condition / routing prompt">
          <Textarea
            value={config.condition ?? ""}
            onChange={(e) => onChange({ condition: e.target.value })}
            placeholder="Route to the agent if the query needs research…"
          />
        </Field>
      )}

      <span className="mt-2 text-[10px] text-muted-foreground">
        Node id: <code>{node.id}</code>
      </span>
    </aside>
  );
}
