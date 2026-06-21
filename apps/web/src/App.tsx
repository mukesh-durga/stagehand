import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { BuilderPage } from "@/features/builder/BuilderPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { RoutingPage } from "@/features/routing/RoutingPage";
import { TemplatesPage } from "@/features/templates/TemplatesPage";
import { UsagePage } from "@/features/usage/UsagePage";
import { RunDetailPage } from "@/features/runs/RunDetailPage";
import { RunDiffPage } from "@/features/runs/RunDiffPage";
import { RunsListPage } from "@/features/runs/RunsListPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { WorkflowsPage } from "@/features/workflows/WorkflowsPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/workflows" element={<WorkflowsPage />} />
        <Route path="/workflows/new" element={<BuilderPage />} />
        <Route path="/workflows/:workflowId/builder" element={<BuilderPage />} />
        <Route path="/runs" element={<RunsListPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/runs/:runId/diff/:otherRunId" element={<RunDiffPage />} />
        <Route path="/routing" element={<RoutingPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/usage" element={<UsagePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
