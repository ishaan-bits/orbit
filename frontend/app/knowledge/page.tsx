"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, FileText, RefreshCw, Search } from "lucide-react";

import { DeleteDocumentDialog } from "@/components/knowledge/delete-document-dialog";
import { DocumentTable } from "@/components/knowledge/document-table";
import { EmptyState } from "@/components/knowledge/empty-state";
import { FolderSidebar } from "@/components/knowledge/folder-sidebar";
import { UploadZone } from "@/components/knowledge/upload-zone";
import { RequireAuth } from "@/components/require-auth";
import { UserMenu } from "@/components/user-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type DocumentMeta, type Folder } from "@/lib/api";

export default function KnowledgePage() {
  return (
    <RequireAuth>
      <KnowledgeContent />
    </RequireAuth>
  );
}

function KnowledgeContent() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [total, setTotal] = useState(0);

  const [activeFolder, setActiveFolder] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const [foldersLoading, setFoldersLoading] = useState(true);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DocumentMeta | null>(null);

  useEffect(() => {
    const initial = new URLSearchParams(window.location.search).get("q");
    if (initial) setQuery(initial);
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), 350);
    return () => clearTimeout(timer);
  }, [query]);

  const loadFolders = useCallback(async () => {
    try {
      setFolders(await api.listFolders());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load folders");
    } finally {
      setFoldersLoading(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      const result = await api.listDocuments({
        folderId: activeFolder,
        q: debouncedQuery || undefined,
      });
      setDocuments(result.items);
      setTotal(result.total);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load documents",
      );
    } finally {
      setDocumentsLoading(false);
    }
  }, [activeFolder, debouncedQuery]);

  useEffect(() => {
    void loadFolders();
  }, [loadFolders]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const refresh = useCallback(async () => {
    await Promise.all([loadFolders(), loadDocuments()]);
  }, [loadFolders, loadDocuments]);

  const activeFolderName =
    activeFolder === null
      ? null
      : (folders.find((folder) => folder.id === activeFolder)?.name ??
        undefined);

  const searchActive = debouncedQuery.length > 0;

  const showEmpty =
    !documentsLoading && documents.length === 0 && error === null;
  const emptyVariant = searchActive
    ? "search"
    : activeFolder === null
      ? "empty"
      : "folder";

  return (
    <div className="min-h-screen">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <FileText className="size-5" />
            </span>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                Knowledge Base
              </h1>
              <p className="text-sm text-muted-foreground">
                Upload and organise your documents
              </p>
            </div>
          </div>
          <div className="flex w-full flex-col gap-4 md:w-auto md:flex-row md:items-center">
            <div className="relative w-full md:w-72">
              <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search documents…"
                aria-label="Search documents"
                className="pl-9"
              />
            </div>
            <UserMenu />
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl gap-8 px-4 py-6 sm:px-6 lg:px-8">
        <aside className="hidden w-56 shrink-0 md:block">
          <FolderSidebar
            folders={folders}
            activeId={activeFolder}
            onSelect={setActiveFolder}
            onCreated={(folder) => {
              void loadFolders().then(() => setActiveFolder(folder.id));
            }}
          />
        </aside>

        <main className="min-w-0 flex-1 space-y-6">
          {/* Mobile folder selector */}
          <div className="flex gap-2 overflow-x-auto pb-1 md:hidden">
            <button
              type="button"
              onClick={() => setActiveFolder(null)}
              className={
                activeFolder === null
                  ? "shrink-0 rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
                  : "shrink-0 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground"
              }
            >
              All documents
            </button>
            {folders.map((folder) => (
              <button
                key={folder.id}
                type="button"
                onClick={() => setActiveFolder(folder.id)}
                className={
                  activeFolder === folder.id
                    ? "shrink-0 rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
                    : "shrink-0 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground"
                }
              >
                {folder.name} ({folder.document_count})
              </button>
            ))}
          </div>

          {error && (
            <div className="flex items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <span className="flex items-center gap-2">
                <AlertTriangle className="size-4 shrink-0" />
                {error}
              </span>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => {
                  setFoldersLoading(true);
                  setDocumentsLoading(true);
                  void refresh();
                }}
              >
                <RefreshCw />
                Retry
              </Button>
            </div>
          )}

          <UploadZone
            folderId={activeFolder}
            onUploaded={() => void refresh()}
          />

          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">
              {searchActive
                ? "Search results"
                : (activeFolderName ?? "All documents")}
            </h2>
            {!documentsLoading && (
              <span className="text-xs text-muted-foreground">
                {total} {total === 1 ? "document" : "documents"}
              </span>
            )}
          </div>

          <DocumentTable
            documents={documents}
            loading={documentsLoading && !foldersLoading}
            onDelete={setDeleteTarget}
          />

          {showEmpty && (
            <EmptyState
              variant={emptyVariant}
              query={debouncedQuery}
              folderName={activeFolderName ?? undefined}
            />
          )}
        </main>
      </div>

      <DeleteDocumentDialog
        document={deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onDeleted={() => {
          setDeleteTarget(null);
          void refresh();
        }}
      />
    </div>
  );
}
