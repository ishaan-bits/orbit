"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ApiError, api, type DocumentMeta } from "@/lib/api";

interface DeleteDocumentDialogProps {
  document: DocumentMeta | null;
  onOpenChange: (open: boolean) => void;
  onDeleted: () => void;
}

export function DeleteDocumentDialog({
  document,
  onOpenChange,
  onDeleted,
}: DeleteDocumentDialogProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmDelete() {
    if (!document || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteDocument(document.id);
      setError(null);
      onDeleted();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not delete the document",
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AlertDialog
      open={document !== null}
      onOpenChange={(open) => {
        if (!open && !deleting) {
          setError(null);
          onOpenChange(false);
        }
      }}
    >
      {document && (
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              “{document.original_filename}” will be removed from the knowledge
              base and its file deleted from storage. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={deleting}
              onClick={() => void confirmDelete()}
            >
              {deleting && <Loader2 className="animate-spin" />}
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      )}
    </AlertDialog>
  );
}
