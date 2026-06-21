import { AlertCircle, Loader2, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, deleteWorkflow, listWorkflows } from "@/lib/api";
import type { Workflow } from "@/types";

export function WorkflowsPage() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setWorkflows(await listWorkflows());
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 0
          ? "Cannot reach the backend API. Is it running?"
          : "Failed to load workflows.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!window.confirm("Delete this workflow and all its versions?")) return;
      try {
        await deleteWorkflow(id);
        setWorkflows((wfs) => wfs.filter((w) => w.id !== id));
      } catch {
        setError("Failed to delete workflow.");
      }
    },
    [],
  );

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Workflows</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Design and manage your multi-agent workflows.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate("/templates")}>
            Start from template
          </Button>
          <Button onClick={() => navigate("/workflows/new")}>
            <Plus className="h-4 w-4" /> New workflow
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading workflows…
        </div>
      ) : workflows.length === 0 && !error ? (
        <Card>
          <CardHeader>
            <CardTitle>No workflows yet</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Create your first workflow to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {workflows.map((wf) => (
            <Card key={wf.id}>
              <div className="flex items-center justify-between p-5">
                <div className="min-w-0">
                  <div className="truncate font-medium">{wf.name}</div>
                  <div className="truncate text-sm text-muted-foreground">
                    {wf.description || "No description"}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {wf.graph.nodes.length} nodes · v{wf.current_version_number ?? 1}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(`/workflows/${wf.id}/builder`)}
                  >
                    Open builder
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => void handleDelete(wf.id)}
                    title="Delete workflow"
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
