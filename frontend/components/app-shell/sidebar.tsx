"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  Settings,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "cn";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  testId: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard" },
  { href: "/workspace", label: "AI Workspace", icon: Sparkles, testId: "nav-workspace" },
  { href: "/knowledge", label: "Knowledge Base", icon: FolderOpen, testId: "nav-knowledge" },
  { href: "/analytics", label: "Analytics", icon: BarChart3, adminOnly: true, testId: "nav-analytics" },
  { href: "/settings", label: "Settings", icon: Settings, testId: "nav-settings" },
];

const baseClass =
  "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card/80 backdrop-blur";

export function Sidebar({
  variant,
  open = true,
  onNavigate,
}: {
  variant: "desktop" | "mobile";
  open?: boolean;
  onNavigate?: () => void;
}) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [signedOut, setSignedOut] = useState(false);

  if (!user) return null;

  const isAdmin = user.role === "Admin";
  const label = user.full_name || user.email;
  const initial = label.charAt(0).toUpperCase();

  async function handleLogout() {
    setSignedOut(true);
    await logout();
    router.replace("/login");
  }

  return (
    <aside
      data-testid={variant === "desktop" ? "sidebar" : "mobile-sidebar"}
      data-open={open}
      className={cn(
        baseClass,
        variant === "desktop" && "hidden md:flex",
        variant === "mobile" &&
          "transition-transform duration-200 md:hidden data-[open=false]:-translate-x-full data-[open=true]:translate-x-0",
      )}
    >
      <nav
        aria-label="Primary"
        className="flex-1 space-y-1 overflow-y-auto p-3 pt-4"
      >
        {NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin).map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              data-testid={item.testId}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition",
                active
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" />
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
              {item.adminOnly ? (
                <span className="rounded border border-border px-1 py-px text-[0.6rem] text-muted-foreground">
                  Admin
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3" data-testid="sidebar-user">
        <div className="flex items-center gap-2.5">
          <span
            className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-foreground uppercase"
            aria-hidden="true"
          >
            {initial}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium" title={label}>
              {label}
            </p>
            <p className="truncate text-[0.7rem] text-muted-foreground" title={user.email}>
              {user.email}
            </p>
          </div>
          <Badge variant="secondary" data-testid="sidebar-role-badge">
            {user.role}
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="mt-2 w-full justify-start gap-2 text-muted-foreground"
          onClick={() => void handleLogout()}
          disabled={signedOut}
          data-testid="sidebar-signout"
        >
          <LogOut className="size-4" />
          Sign out
        </Button>
      </div>
    </aside>
  );
}

/** Mobile drawer that closes on route change and Escape. */
export function MobileSidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();

  useEffect(() => {
    onClose();
  }, [pathname, onClose]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      <div
        data-testid="sidebar-backdrop"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-black/50 transition-opacity md:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <Sidebar variant="mobile" open={open} onNavigate={onClose} />
    </>
  );
}
