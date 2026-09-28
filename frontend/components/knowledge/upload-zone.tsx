"use client";

import { useRef, useState } from "react";
import { CheckCircle2, CloudUpload, Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "cn";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];
const MAX_FILE_SIZE = 25 * 1024 * 1024;

interface UploadItem {
  name: string;
  state: "uploading" | "done" | "error";
  message?: string;
}

interface UploadZoneProps {
  folderId: string | null;
  disabled?: boolean;
  onUploaded: () => void;
}

function updateLastUploading(
  items: UploadItem[],
  name: string,
  patch: Partial<UploadItem>,
): UploadItem[] {
  const next = [...items];
  for (let i = next.length - 1; i >= 0; i -= 1) {
    if (next[i].name === name && next[i].state === "uploading") {
      next[i] = { ...next[i], ...patch };
      break;
    }
  }
  return next;
}

export function UploadZone({ folderId, disabled, onUploaded }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const [busy, setBusy] = useState(false);

  async function handleFiles(list: FileList | File[]) {
    const files = Array.from(list);
    if (files.length === 0 || busy) return;

    setBusy(true);
    let uploaded = 0;

    for (const file of files) {
      const accepted = ACCEPTED_EXTENSIONS.some((ext) =>
        file.name.toLowerCase().endsWith(ext),
      );
      if (!accepted) {
        setItems((prev) => [
          ...prev,
          {
            name: file.name,
            state: "error",
            message: "Unsupported type — use PDF, DOCX, TXT or Markdown",
          },
        ]);
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        setItems((prev) => [
          ...prev,
          { name: file.name, state: "error", message: "Exceeds the 25MB limit" },
        ]);
        continue;
      }

      setItems((prev) => [...prev, { name: file.name, state: "uploading" }]);
      try {
        const doc = await api.uploadDocument(file, folderId);
        const indexed = await api.indexDocument(doc.id);
        if (indexed.status === "pending_retry" || indexed.status === "processing") {
          // pending_retry: HTTP 429 quota, re-indexed later by the cron.
          // processing: the server-side auto-index (or a cron retry) is
          // already running this document — either way not an upload error.
          uploaded += 1;
          setItems((prev) =>
            updateLastUploading(prev, file.name, { state: "done" }),
          );
          continue;
        }
        if (indexed.status !== "indexed") {
          throw new Error(indexed.error ?? "Indexing failed");
        }
        uploaded += 1;
        setItems((prev) => updateLastUploading(prev, file.name, { state: "done" }));
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Upload failed";
        setItems((prev) =>
          updateLastUploading(prev, file.name, { state: "error", message }),
        );
      }
    }

    setBusy(false);
    if (uploaded > 0) onUploaded();
  }

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload documents"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) void handleFiles(event.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border bg-card/50 px-6 py-10 text-center transition-colors outline-none",
          "hover:border-ring/60 hover:bg-muted/30 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
          dragging && "border-ring bg-muted/50",
          disabled && "pointer-events-none opacity-60",
        )}
      >
        <span className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <CloudUpload className="size-5" />
        </span>
        <p className="text-sm font-medium text-foreground">
          Drag &amp; drop files here, or click to browse
        </p>
        <p className="text-xs text-muted-foreground">
          PDF, DOCX, TXT, Markdown · up to 25MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(event) => {
            if (event.target.files) void handleFiles(event.target.files);
            event.target.value = "";
          }}
        />
      </div>

      {items.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              Uploads
            </span>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => setItems([])}
              aria-label="Clear upload list"
            >
              <X />
            </Button>
          </div>
          <ul className="space-y-1.5">
            {items.map((item, index) => (
              <li
                key={`${item.name}-${index}`}
                className="flex items-start justify-between gap-3 text-sm"
              >
                <span className="min-w-0 break-all text-foreground">
                  {item.name}
                </span>
                <span className="flex shrink-0 items-center gap-1.5 text-xs">
                  {item.state === "uploading" && (
                    <>
                      <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                      <span className="text-muted-foreground">Uploading…</span>
                    </>
                  )}
                  {item.state === "done" && (
                    <>
                      <CheckCircle2 className="size-3.5 text-emerald-500" />
                      <span className="text-muted-foreground">Uploaded</span>
                    </>
                  )}
                  {item.state === "error" && (
                    <>
                      <X className="size-3.5 text-destructive" />
                      <span className="text-destructive">{item.message}</span>
                    </>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
