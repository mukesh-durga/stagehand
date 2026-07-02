import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { BuilderPage } from "@/features/builder/BuilderPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { LandingPage } from "@/features/public/LandingPage";
import { SignInPage } from "@/features/public/SignInPage";
import { SignUpPage } from "@/features/public/SignUpPage";
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
      {/* Public marketing + auth pages (no app shell). */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/signin" element={<SignInPage />} />
      <Route path="/signup" element={<SignUpPage />} />
      {/* Back-compat: the old /login route now points at sign in. */}
      <Route path="/login" element={<Navigate to="/signin" replace />} />

      {/* App pages (inside the sidebar/header shell). Not route-guarded so deep
          links keep working; the landing/auth pages drive demo entry. */}
      <Route element={<AppShell />}>
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
