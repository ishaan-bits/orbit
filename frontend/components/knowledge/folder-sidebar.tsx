"use client";

import { useState } from "react";
import { FolderOpen, LayoutList, Loader2, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api, type Folder } from "@/lib/api";
import { cn } from "cn";

interface FolderSidebarProps {
  folders: Folder[];
  activeId: string | null;
  onSelect: (folderId: string | null) => void;
  onCreated: (folder: Folder) => void;
}

export function FolderSidebar({
  folders,
  activeId,
  onSelect,
  onCreated,
}: FolderSidebarProps) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const trimmed = name.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const folder = await api.createFolder(trimmed);
      setName("");
      setCreating(false);
      onCreated(folder);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not create folder",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const itemClass = (active: boolean) =>
    cn(
      "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors outline-none",
      "focus-visible:ring-3 focus-visible:ring-ring/50",
      active
        ? "bg-muted font-medium text-foreground"
        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
    );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          Folders
        </h2>
        <Button
          variant="ghost"
          size="xs"
          onClick={() => {
            setCreating((value) => !value);
            setError(null);
          }}
          aria-label="New folder"
        >
          <Plus />
        </Button>
      </div>

      {creating && (
        <div className="space-y-2">
          <Input
            autoFocus
            value={name}
            maxLength={100}
            placeholder="Folder name"
            onChange={(event) => setName(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void submit();
              if (event.key === "Escape") setCreating(false);
            }}
          />
          <div className="flex gap-2">
            <Button size="xs" onClick={() => void submit()} disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" />}
              Create
            </Button>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => {
                setCreating(false);
                setName("");
                setError(null);
              }}
            >
              Cancel
            </Button>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}

      <nav className="space-y-1">
        <button
          type="button"
          onClick={() => onSelect(null)}
          className={itemClass(activeId === null)}
        >
          <LayoutList className="size-4 shrink-0" />
          <span className="min-w-0 flex-1 truncate">All documents</span>
        </button>

        {folders.map((folder) => (
          <button
            key={folder.id}
            type="button"
            onClick={() => onSelect(folder.id)}
            className={itemClass(activeId === folder.id)}
          >
            <FolderOpen className="size-4 shrink-0" />
            <span className="min-w-0 flex-1 truncate">{folder.name}</span>
            <Badge variant="secondary">{folder.document_count}</Badge>
          </button>
        ))}
      </nav>
    </div>
  );
}
