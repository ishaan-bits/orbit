"use client";

import { FileText, FolderOpen, Loader2, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DocumentMeta } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";

interface DocumentTableProps {
  documents: DocumentMeta[];
  loading: boolean;
  onDelete: (document: DocumentMeta) => void;
}

function DeleteButton({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={onClick}
      aria-label={`Delete ${label}`}
      className="text-muted-foreground hover:text-destructive"
    >
      <Trash2 />
    </Button>
  );
}

function statusLabel(document: DocumentMeta): string {
  switch (document.status) {
    case "indexed": {
      const chunks = `${document.chunk_count} chunk${document.chunk_count === 1 ? "" : "s"}`;
      return `Indexed · ${chunks}`;
    }
    case "processing":
      return "Indexing…";
    case "failed":
      return "Indexing failed";
    default:
      return "Not indexed";
  }
}

function StatusBadge({ document }: { document: DocumentMeta }) {
  if (document.status === "indexed") {
    return (
      <Badge
        variant="outline"
        className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
      >
        {statusLabel(document)}
      </Badge>
    );
  }
  if (document.status === "processing") {
    return (
      <Badge variant="secondary">
        <Loader2 className="size-3 animate-spin" /> Indexing…
      </Badge>
    );
  }
  if (document.status === "failed") {
    return (
      <Badge variant="destructive" title={document.index_error ?? undefined}>
        Indexing failed
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-muted-foreground">
      Not indexed
    </Badge>
  );
}

function SkeletonRows() {
  return (
    <>
      {[0, 1, 2, 3].map((row) => (
        <TableRow key={row}>
          <TableCell>
            <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          </TableCell>
          <TableCell>
            <div className="h-4 w-20 animate-pulse rounded bg-muted" />
          </TableCell>
          <TableCell>
            <div className="h-4 w-14 animate-pulse rounded bg-muted" />
          </TableCell>
          <TableCell>
            <div className="h-4 w-28 animate-pulse rounded bg-muted" />
          </TableCell>
          <TableCell>
            <div className="h-5 w-24 animate-pulse rounded-full bg-muted" />
          </TableCell>
          <TableCell className="w-10" />
        </TableRow>
      ))}
    </>
  );
}

export function DocumentTable({
  documents,
  loading,
  onDelete,
}: DocumentTableProps) {
  return (
    <div className="space-y-4">
      {/* Desktop */}
      <div className="hidden overflow-hidden rounded-xl border border-border bg-card md:block">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Name</TableHead>
              <TableHead>Folder</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-10 text-right">
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <SkeletonRows />
            ) : (
              documents.map((document) => (
                <TableRow key={document.id}>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                        <FileText className="size-4" />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-foreground">
                          {document.original_filename}
                        </p>
                        <Badge variant="outline" className="mt-0.5">
                          {document.file_extension.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {document.folder_name ?? (
                      <span className="inline-flex items-center gap-1.5">
                        <FolderOpen className="size-3.5" /> Unfiled
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatBytes(document.file_size)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(document.created_at)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge document={document} />
                  </TableCell>
                  <TableCell className="text-right">
                    <DeleteButton
                      label={document.original_filename}
                      onClick={() => onDelete(document)}
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Mobile */}
      <div className="space-y-2 md:hidden">
        {loading ? (
          [0, 1, 2].map((row) => (
            <div
              key={row}
              className="h-20 animate-pulse rounded-xl border border-border bg-card"
            />
          ))
        ) : (
          documents.map((document) => (
            <div
              key={document.id}
              className="flex items-start gap-3 rounded-xl border border-border bg-card p-3"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <FileText className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {document.original_filename}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {document.folder_name ?? "Unfiled"} ·{" "}
                  {formatBytes(document.file_size)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDate(document.created_at)} · {statusLabel(document)}
                </p>
              </div>
              <DeleteButton
                label={document.original_filename}
                onClick={() => onDelete(document)}
              />
            </div>
          ))
        )}
      </div>

      {loading && documents.length === 0 && (
        <p className="flex items-center justify-center gap-2 py-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading documents…
        </p>
      )}
    </div>
  );
}
