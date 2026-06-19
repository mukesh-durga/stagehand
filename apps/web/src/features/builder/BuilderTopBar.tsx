import { AlertCircle, ArrowLeft, Check, Loader2, Play, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useBuilderStore } from "@/stores/builderStore";

interface BuilderTopBarProps {
  onSave: () => void;
  onBack: () => void;
  onRun: () => void;
  canRun: boolean;
}

export function BuilderTopBar({ onSave, onBack, onRun, canRun }: BuilderTopBarProps) {
  const {
    workflowName,
    workflowDescription,
    saveStatus,
    validationErrors,
    setWorkflowName,
    setWorkflowDescription,
  } = useBuilderStore();

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2">
        <Button size="icon" variant="ghost" onClick={onBack} title="Back to workflows">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Input
          className="max-w-xs font-medium"
          placeholder="Workflow name"
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
        />
        <Input
          className="flex-1"
          placeholder="Description (optional)"
          value={workflowDescription}
          onChange={(e) => setWorkflowDescription(e.target.value)}
        />
        <div className="flex min-w-[88px] items-center justify-end text-xs text-muted-foreground">
          {saveStatus === "saving" && (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
            </span>
          )}
          {saveStatus === "saved" && (
            <span className="flex items-center gap-1 text-success">
              <Check className="h-3.5 w-3.5" /> Saved
            </span>
          )}
          {saveStatus === "error" && (
            <span className="flex items-center gap-1 text-destructive">
              <AlertCircle className="h-3.5 w-3.5" /> Error
            </span>
          )}
        </div>
        <Button size="sm" variant="outline" onClick={onSave} disabled={saveStatus === "saving"}>
          <Save className="h-3.5 w-3.5" /> Save
        </Button>
        <Button
          size="sm"
          onClick={onRun}
          disabled={!canRun}
          title={canRun ? "Run workflow" : "Save the workflow first"}
        >
          <Play className="h-3.5 w-3.5" /> Run
        </Button>
      </div>

      {validationErrors.length > 0 && (
        <ul className="flex flex-col gap-1 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {validationErrors.map((err) => (
            <li key={err} className="flex items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {err}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
