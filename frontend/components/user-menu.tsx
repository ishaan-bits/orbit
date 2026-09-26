"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!user) return null;

  const label = user.full_name || user.email;
  const initial = label.charAt(0).toUpperCase();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="flex items-center gap-2.5" data-testid="user-menu">
      <span
        className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-foreground uppercase"
        aria-hidden="true"
      >
        {initial}
      </span>
      <div className="hidden min-w-0 sm:block">
        <p className="max-w-40 truncate text-xs font-medium" title={user.email}>
          {label}
        </p>
        <p className="max-w-40 truncate text-[0.7rem] text-muted-foreground">
          {user.email}
        </p>
      </div>
      <Badge variant="secondary" data-testid="role-badge">
        {user.role}
      </Badge>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleLogout}
        aria-label="Sign out"
      >
        <LogOut />
        <span className="hidden sm:inline">Sign out</span>
      </Button>
    </div>
  );
}
