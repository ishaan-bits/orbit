"use client";

import Link from "next/link";
import { BookOpen, LayoutDashboard, Loader2, Plus, Sparkles } from "lucide-react";

import { UserMenu } from "@/components/user-menu";
import { Button } from "@/components/ui/button";
import type { ChatConversation } from "@/lib/api";
import { cn } from "cn";

interface ConversationSidebarProps {
  conversations: ChatConversation[];
  activeId: string | null;
  loading: boolean;
  disabled: boolean;
  onSelect: (conversation: ChatConversation) => void;
  onNewChat: () => void;
}

export function ConversationSidebar({
  conversations,
  activeId,
  loading,
  disabled,
  onSelect,
  onNewChat,
}: ConversationSidebarProps) {
  const itemClass = (active: boolean) =>
    cn(
      "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors outline-none",
      "focus-visible:ring-3 focus-visible:ring-ring/50",
      active
        ? "bg-muted font-medium text-foreground"
        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
    );

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-3 py-4">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Sparkles className="size-4" />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-tight">Orbit</p>
          <p className="text-[0.7rem] text-muted-foreground">AI Workspace</p>
        </div>
      </div>

      <div className="px-3 pb-3">
        <Button
          className="w-full justify-start"
          onClick={onNewChat}
          disabled={disabled}
        >
          <Plus />
          New conversation
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3">
        <h2 className="px-2.5 py-2 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          History
        </h2>

        {loading ? (
          <p className="flex items-center gap-2 px-2.5 py-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            Loading…
          </p>
        ) : conversations.length === 0 ? (
          <p className="px-2.5 py-2 text-xs text-muted-foreground">
            No conversations yet.
          </p>
        ) : (
          <nav className="space-y-1">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                disabled={disabled}
                onClick={() => onSelect(conversation)}
                className={itemClass(activeId === conversation.id)}
              >
                <span className="min-w-0 flex-1 truncate">
                  {conversation.title}
                </span>
                <span className="shrink-0 text-[0.7rem] tabular-nums text-muted-foreground/70">
                  {conversation.messages.length}
                </span>
              </button>
            ))}
          </nav>
        )}
      </div>

      <nav className="space-y-1 border-t border-border p-3">
        <Link
          href="/knowledge"
          className={itemClass(false)}
        >
          <BookOpen className="size-4 shrink-0" />
          <span className="min-w-0 flex-1 truncate">Knowledge Base</span>
        </Link>
        <Link
          href="/dashboard"
          className={itemClass(false)}
        >
          <LayoutDashboard className="size-4 shrink-0" />
          <span className="min-w-0 flex-1 truncate">Dashboard</span>
        </Link>
        <div className="mt-2 border-t border-border pt-3">
          <UserMenu />
        </div>
      </nav>
    </div>
  );
}
