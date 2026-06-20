import { Badge } from "@/components/ui/badge";

export function RunStatusBadge({ status }: { status: string }) {
  const variant =
    status === "completed"
      ? "success"
      : status === "failed"
        ? "destructive"
        : status === "running" || status === "queued"
          ? "default"
          : "muted";
  return <Badge variant={variant}>{status}</Badge>;
}
