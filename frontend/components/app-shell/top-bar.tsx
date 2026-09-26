"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { OrbitMark } from "@/components/landing/logo";

const PAGE_LABELS: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/workspace": "AI Workspace",
  "/knowledge": "Knowledge Base",
  "/analytics": "Analytics",
  "/settings": "Settings",
};

export function TopBar({ onMenuToggle }: { onMenuToggle: () => void }) {
  const pathname = usePathname();
  const pageLabel = PAGE_LABELS[pathname] ?? "Dashboard";

  return (
    <header
      data-testid="top-bar"
      className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur md:px-6"
    >
      <button
        type="button"
        onClick={onMenuToggle}
        aria-label="Open navigation"
        data-testid="mobile-sidebar-toggle"
        className="flex size-9 items-center justify-center rounded-lg border border-border/60 text-muted-foreground transition hover:text-foreground md:hidden"
      >
        <Menu className="size-5" />
      </button>

      <Link
        href="/dashboard"
        className="flex items-center gap-2"
        aria-label="Orbit home"
      >
        <OrbitMark className="size-6 text-primary" />
        <span className="text-sm font-semibold tracking-tight">Orbit</span>
      </Link>

      <span aria-hidden="true" className="text-muted-foreground/60">
        /
      </span>

      <nav
        aria-label="Breadcrumb"
        data-testid="breadcrumb"
        className="flex min-w-0 items-center gap-1.5 text-sm"
      >
        <Link
          href="/dashboard"
          className="text-muted-foreground transition hover:text-foreground"
        >
          Home
        </Link>
        <span aria-hidden="true" className="text-muted-foreground/60">
          /
        </span>
        <span
          className="truncate font-medium text-foreground"
          data-testid="breadcrumb-current"
        >
          {pageLabel}
        </span>
      </nav>
    </header>
  );
}
