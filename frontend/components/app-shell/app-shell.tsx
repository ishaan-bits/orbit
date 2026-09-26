"use client";

import { useCallback, useState } from "react";

import { RequireAuth } from "@/components/require-auth";
import { MobileSidebar, Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";

/** Persistent authenticated chrome: sidebar + top breadcrumb bar. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const closeSidebar = useCallback(() => setMobileOpen(false), []);

  return (
    <RequireAuth>
      <div className="min-h-screen">
        <Sidebar variant="desktop" />

        <MobileSidebar open={mobileOpen} onClose={closeSidebar} />

        <div className="flex min-h-screen flex-col md:pl-64">
          <TopBar onMenuToggle={() => setMobileOpen((open) => !open)} />
          <main className="flex-1">{children}</main>
        </div>
      </div>
    </RequireAuth>
  );
}
