import { Workflow } from "lucide-react";
import { type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { enterDemo } from "@/lib/demo";

export function SignInPage() {
  const navigate = useNavigate();

  const enter = () => {
    enterDemo();
    navigate("/dashboard");
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    enter();
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-6 py-12">
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/10 via-background to-background" />
      <div aria-hidden className="pointer-events-none absolute -top-40 left-1/2 h-[32rem] w-[32rem] -translate-x-1/2 rounded-full bg-primary/15 blur-3xl" />

      <div className="relative z-10 w-full max-w-sm">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2">
          <Workflow className="h-5 w-5 text-primary" />
          <span className="text-lg font-semibold tracking-tight">Stagehand</span>
        </Link>

        <div className="rounded-xl border border-border bg-card p-6 shadow-lg">
          <h1 className="text-center text-xl font-semibold tracking-tight">Sign in to Stagehand</h1>

          <form className="mt-6 flex flex-col gap-4" onSubmit={onSubmit}>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="you@example.com" autoComplete="email" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" placeholder="••••••••" autoComplete="current-password" />
            </div>
            <Button type="submit" className="mt-1 h-10">Sign In</Button>
          </form>

          <div className="my-4 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="h-px flex-1 bg-border" />
            or
            <span className="h-px flex-1 bg-border" />
          </div>

          <Button variant="outline" className="h-10 w-full" onClick={enter}>
            Continue
          </Button>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link to="/signup" className="font-medium text-primary hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
