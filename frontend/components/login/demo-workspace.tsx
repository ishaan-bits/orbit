"use client";

import { useRef, useState } from "react";
import { Check, Copy } from "lucide-react";

import { DEMO_COMPANY, DEMO_PASSWORD, DEMO_USERS } from "@/lib/site";

/** Glass card with one-click demo accounts for the sign-in form. */
export function DemoWorkspace({
  onPickEmail,
}: {
  onPickEmail: (email: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function copyPassword() {
    try {
      await navigator.clipboard.writeText(DEMO_PASSWORD);
    } catch {
      // Clipboard unavailable — still confirm visually for manual copying.
    }
    setCopied(true);
    if (resetTimer.current) clearTimeout(resetTimer.current);
    resetTimer.current = setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div
      data-testid="demo-workspace"
      className="rounded-xl border border-border/60 bg-card/40 p-3 backdrop-blur"
    >
      <div className="flex items-center justify-between px-1 pb-2">
        <span className="text-xs font-semibold tracking-wide text-foreground">
          Demo Workspace
        </span>
        <span className="text-[0.7rem] text-muted-foreground">
          {DEMO_COMPANY}
        </span>
      </div>

      <div className="flex flex-col gap-1.5">
        {DEMO_USERS.map((account) => (
          <button
            key={account.email}
            type="button"
            data-testid={`demo-row-${account.role.toLowerCase()}`}
            onClick={() => onPickEmail(account.email)}
            className="flex items-center justify-between gap-2 rounded-lg border border-border/50 bg-background/60 px-2.5 py-2 text-left transition hover:border-primary/50 hover:bg-primary/5"
          >
            <span className="text-sm font-medium">{account.role}</span>
            <span className="truncate font-mono text-xs text-muted-foreground">
              {account.email}
            </span>
          </button>
        ))}
      </div>

      <div className="mt-2.5 flex items-center justify-between border-t border-border/60 px-1 pt-2.5">
        <span className="text-xs text-muted-foreground">Password</span>
        <button
          type="button"
          onClick={() => void copyPassword()}
          data-testid="demo-password"
          aria-label="Copy demo password"
          className="flex items-center gap-1.5 rounded-md px-1.5 py-1 font-mono text-xs text-foreground transition hover:bg-muted"
        >
          {DEMO_PASSWORD}
          {copied ? (
            <Check className="size-3.5 text-primary" data-testid="demo-copied" />
          ) : (
            <Copy className="size-3.5 text-muted-foreground" />
          )}
        </button>
      </div>
    </div>
  );
}
