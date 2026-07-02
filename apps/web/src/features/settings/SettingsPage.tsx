import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/lib/api";
import { leaveDemo } from "@/lib/demo";

export function SettingsPage() {
  const navigate = useNavigate();

  const handleLeaveDemo = () => {
    leaveDemo();
    navigate("/");
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Application configuration.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API connection</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <span className="text-muted-foreground">Base URL: </span>
          <code>{API_BASE_URL}</code>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          <p className="text-muted-foreground">
            Sign out of this workspace and return to the public site.
          </p>
          <Button variant="outline" className="w-fit" onClick={handleLeaveDemo}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
