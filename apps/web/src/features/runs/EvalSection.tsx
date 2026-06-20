import { Loader2, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRunEvals, runEval } from "@/lib/api";
import type { EvalResult } from "@/types";

const SCORE_FIELDS: { key: keyof EvalResult; label: string }[] = [
  { key: "success_score", label: "success" },
  { key: "tool_correctness_score", label: "tool" },
  { key: "format_score", label: "format" },
  { key: "quality_score", label: "quality" },
  { key: "cost_score", label: "cost" },
  { key: "latency_score", label: "latency" },
];

export function EvalSection({ runId }: { runId: string }) {
  const [evals, setEvals] = useState<EvalResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setEvals(await getRunEvals(runId));
    } catch {
      setError("Failed to load evals.");
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleRunEval = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      await runEval(runId, {
        eval_types: ["latency", "cost", "llm_as_judge"],
        max_latency_ms: 5000,
        max_cost_usd: 0.05,
      });
      await load();
    } catch {
      setError("Failed to run eval.");
    } finally {
      setRunning(false);
    }
  }, [runId, load]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Evals ({evals.length})</CardTitle>
        <Button size="sm" onClick={() => void handleRunEval()} disabled={running}>
          {running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Run eval
        </Button>
      </CardHeader>
      <CardContent>
        {error && <div className="mb-2 text-sm text-destructive">{error}</div>}
        {evals.length === 0 ? (
          <span className="text-sm text-muted-foreground">
            No evals yet. Click “Run eval” to score this run.
          </span>
        ) : (
          <ul className="flex flex-col gap-2">
            {evals.map((e) => (
              <li key={e.id} className="rounded-md border border-border p-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm">{e.eval_type}</span>
                  <Badge variant={e.passed ? "success" : "destructive"}>
                    {e.passed ? "passed" : "failed"}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    score {e.success_score.toFixed(2)}
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {new Date(e.created_at).toLocaleString()}
                  </span>
                </div>
                {e.feedback && (
                  <div className="mt-1 text-xs text-muted-foreground">{e.feedback}</div>
                )}
                <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  {SCORE_FIELDS.map(({ key, label }) => {
                    const v = e[key];
                    return typeof v === "number" ? (
                      <span key={label} className="rounded bg-secondary px-1.5 py-0.5">
                        {label}: {v.toFixed(2)}
                      </span>
                    ) : null;
                  })}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
