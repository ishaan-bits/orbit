"use client";

import Link from "next/link";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function ViewerRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div
        className="w-full max-w-md space-y-3 rounded-2xl border border-border bg-card p-8 text-center"
        data-testid="viewer-route-error"
      >
        <AlertTriangle className="mx-auto size-10 text-amber-500" />
        <h1 className="text-lg font-semibold">Could not open this document</h1>
        <p className="text-sm text-muted-foreground">
          Something went wrong while rendering the viewer.
          {error.digest ? ` (error ${error.digest})` : ""}
        </p>
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            onClick={reset}
            data-testid="viewer-route-error-retry"
          >
            Try again
          </Button>
          <Button
            render={<Link href="/knowledge" />}
            nativeButton={false}
            variant="outline"
          >
            Back to Knowledge Base
          </Button>
        </div>
      </div>
    </div>
  );
}
