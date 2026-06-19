import { Badge } from "@/components/ui/badge";
import type { ServiceStatus } from "@/types";

const labels: Record<ServiceStatus, string> = {
  unknown: "Unknown",
  checking: "Checking…",
  online: "Online",
  offline: "Offline",
};

const variants = {
  unknown: "muted",
  checking: "muted",
  online: "success",
  offline: "destructive",
} as const;

export function StatusBadge({ status }: { status: ServiceStatus }) {
  return <Badge variant={variants[status]}>{labels[status]}</Badge>;
}
