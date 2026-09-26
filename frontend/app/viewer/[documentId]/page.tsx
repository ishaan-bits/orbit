"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";

import { RequireAuth } from "@/components/require-auth";

/**
 * pdf.js touches `document`/`window` at module scope, so the viewer content
 * (react-pdf) is loaded client-only. `ssr: false` keeps the route server-safe.
 */
const Viewer = dynamic(
  () =>
    import("./viewer-content").then((module) => ({
      default: module.Viewer,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex min-h-screen flex-col bg-background">
        <div className="h-14 border-b border-border" />
        <div
          className="flex flex-1 items-center justify-center gap-2 text-muted-foreground"
          data-testid="viewer-loading"
        >
          <Loader2 className="size-5 animate-spin" />
          <span className="text-sm">Loading document…</span>
        </div>
      </div>
    ),
  },
);

export default function ViewerPage() {
  const params = useParams<{ documentId: string }>();

  return (
    <RequireAuth>
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" />
          </div>
        }
      >
        <Viewer documentId={params.documentId} />
      </Suspense>
    </RequireAuth>
  );
}
