import { StatusBadge } from "@/components/ui/status-badge";
import { useAppStore } from "@/stores/appStore";

export function Header() {
  const backendStatus = useAppStore((s) => s.backendStatus);
  const dbStatus = useAppStore((s) => s.dbStatus);

  return (
    <header className="flex h-14 items-center justify-between border-b border-border px-6">
      <span className="text-sm text-muted-foreground">
        Multi-Agent Workflow Builder with Live Execution Tracing
      </span>
      <div className="flex items-center gap-4 text-xs">
        <span className="flex items-center gap-2">
          <span className="text-muted-foreground">API</span>
          <StatusBadge status={backendStatus} />
        </span>
        <span className="flex items-center gap-2">
          <span className="text-muted-foreground">DB</span>
          <StatusBadge status={dbStatus} />
        </span>
      </div>
    </header>
  );
}
