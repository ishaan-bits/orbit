"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Loader2,
  ShieldAlert,
} from "lucide-react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { OrbitMark } from "@/components/landing/logo";
import { Button } from "@/components/ui/button";
import { api, ApiError, documentFileUrl, type DocumentMeta } from "@/lib/api";
import { formatBytes } from "@/lib/format";
import { cn } from "cn";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

const TEXT_EXTENSIONS = new Set(["txt", "md", "markdown"]);

function parseCitedPage(raw: string | null): number | null {
  const value = Number.parseInt(raw ?? "", 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

function ViewerLoading({ label = "Loading document…" }: { label?: string }) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="h-14 border-b border-border" />
      <div
        className="flex flex-1 items-center justify-center gap-2 text-muted-foreground"
        data-testid="viewer-loading"
      >
        <Loader2 className="size-5 animate-spin" />
        <span className="text-sm">{label}</span>
      </div>
    </div>
  );
}

function ViewerError({
  status,
  filename,
}: {
  status: number;
  filename?: string;
}) {
  const forbidden = status === 403;
  const missing = status === 404;
  const title = forbidden
    ? "You don't have access to this document"
    : missing
      ? "Document not found"
      : "Could not load this document";
  const detail = forbidden
    ? "Your role does not include the folder that holds this file. Ask an administrator for access."
    : missing
      ? "It may have been deleted, or the link is no longer valid."
      : "The Orbit API could not be reached. Check your connection and try again.";

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div
        className="w-full max-w-md space-y-3 rounded-2xl border border-border bg-card p-8 text-center"
        data-testid="viewer-error"
      >
        {forbidden ? (
          <ShieldAlert className="mx-auto size-10 text-destructive" />
        ) : (
          <AlertTriangle className="mx-auto size-10 text-amber-500" />
        )}
        <h1 className="text-lg font-semibold">{title}</h1>
        {filename && (
          <p className="truncate text-sm text-muted-foreground">{filename}</p>
        )}
        <p className="text-sm text-muted-foreground">{detail}</p>
        <Button
          render={<Link href="/knowledge" />}
          nativeButton={false}
          variant="outline"
          data-testid="viewer-error-back"
        >
          Back to Knowledge Base
        </Button>
      </div>
    </div>
  );
}

export function Viewer({ documentId }: { documentId: string }) {
  const searchParams = useSearchParams();
  const citedPage = parseCitedPage(searchParams.get("page"));

  const [meta, setMeta] = useState<DocumentMeta | null>(null);
  const [metaError, setMetaError] = useState<ApiError | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(citedPage ?? 1);
  const [draft, setDraft] = useState(String(citedPage ?? 1));
  const [fileError, setFileError] = useState<string | null>(null);
  const [textBody, setTextBody] = useState<string | null>(null);
  const [backHref, setBackHref] = useState("/knowledge");
  const [mounted, setMounted] = useState<Set<number>>(() => new Set<number>());
  const [width, setWidth] = useState(0);

  const mainRef = useRef<HTMLElement | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const scrolledToCited = useRef(false);
  const programmaticScrollUntil = useRef(0);

  const isPdf = meta?.file_extension?.toLowerCase() === "pdf";
  const isText = TEXT_EXTENSIONS.has(
    (meta?.file_extension ?? "").toLowerCase(),
  );
  const fileUrl = documentFileUrl(documentId);
  /* stable identity: react-pdf keys its cache on `file`, a fresh object every
     render would reload (and unmount) the whole PDF on each state change */
  const pdfFile = useMemo(() => ({ url: fileUrl }), [fileUrl]);
  const pageWidth = Math.max(220, Math.min(width, 940));

  /* load metadata (RBAC enforced by the API) */
  useEffect(() => {
    let alive = true;
    setMeta(null);
    setMetaError(null);
    setNumPages(0);
    scrolledToCited.current = false;
    api
      .getDocument(documentId)
      .then((doc) => {
        if (alive) setMeta(doc);
      })
      .catch((error: unknown) => {
        if (!alive) return;
        setMetaError(
          error instanceof ApiError
            ? error
            : new ApiError("Could not load the document", 0),
        );
      });
    return () => {
      alive = false;
    };
  }, [documentId]);

  /* browser tab shows the filename */
  useEffect(() => {
    if (!meta) return;
    const previous = document.title;
    document.title = `${meta.original_filename} · Orbit`;
    return () => {
      document.title = previous;
    };
  }, [meta]);

  /* return to the page that opened the viewer (chat or knowledge list) */
  useEffect(() => {
    try {
      const referrer = document.referrer;
      if (!referrer) return;
      const url = new URL(referrer);
      if (url.origin === window.location.origin) {
        setBackHref(`${url.pathname}${url.search}`);
      }
    } catch {
      // fall through to the default target
    }
  }, []);

  /* plain-text preview for .txt / .md documents */
  useEffect(() => {
    if (!meta || isPdf || !isText) return;
    let alive = true;
    setTextBody(null);
    setFileError(null);
    fetch(fileUrl, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error("preview fetch failed");
        return response.text();
      })
      .then((body) => {
        if (alive) setTextBody(body);
      })
      .catch(() => {
        if (alive) setFileError("Preview failed to load.");
      });
    return () => {
      alive = false;
    };
  }, [meta, isPdf, isText, fileUrl]);

  /* measure the container so pages scale to any viewport */
  useEffect(() => {
    const element = mainRef.current;
    if (!element || !isPdf) return;
    const update = () => setWidth(element.clientWidth);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [isPdf, meta]);

  /* progressively mount page canvases near the viewport + track current page */
  useEffect(() => {
    if (!numPages) return;
    const mountObserver = new IntersectionObserver(
      (entries) => {
        setMounted((previous) => {
          let changed = false;
          const next = new Set(previous);
          for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            const pageNo = Number(
              (entry.target as HTMLElement).dataset.pageNo,
            );
            if (!next.has(pageNo)) {
              next.add(pageNo);
              changed = true;
            }
          }
          return changed ? next : previous;
        });
      },
      { rootMargin: "800px 0px" },
    );
    const currentObserver = new IntersectionObserver(
      (entries) => {
        if (Date.now() < programmaticScrollUntil.current) return;
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const pageNo = Number((entry.target as HTMLElement).dataset.pageNo);
          setCurrentPage((previous) => (previous === pageNo ? previous : pageNo));
        }
      },
      { rootMargin: "-45% 0px -45% 0px" },
    );
    for (const element of pageRefs.current.values()) {
      mountObserver.observe(element);
      currentObserver.observe(element);
    }
    return () => {
      mountObserver.disconnect();
      currentObserver.disconnect();
    };
  }, [numPages]);

  /* jump to (and highlight) the cited page exactly once on open */
  useEffect(() => {
    if (!numPages || !citedPage || scrolledToCited.current) return;
    const target = Math.min(citedPage, numPages);
    setMounted((previous) => {
      const next = new Set(previous);
      let changed = false;
      for (let page = Math.max(1, target - 1); page <= Math.min(numPages, target + 1); page += 1) {
        if (!next.has(page)) {
          next.add(page);
          changed = true;
        }
      }
      return changed ? next : previous;
    });
  }, [numPages, citedPage]);

  /* scroll once the cited page wrapper actually exists (refs attach at commit) */
  useEffect(() => {
    if (!numPages || !citedPage || scrolledToCited.current) return;
    const target = Math.min(citedPage, numPages);
    if (!pageRefs.current.has(target)) return;
    scrolledToCited.current = true;
    programmaticScrollUntil.current = Date.now() + 900;
    setCurrentPage(target);
    setDraft(String(target));
    // wait until every page wrapper has real layout height, then jump once.
    // (scrollIntoView mis-computes — or no-ops — while pages are still sizing)
    requestAnimationFrame(() => {
      const startedAt = Date.now();
      const jump = () => {
        const element = document.getElementById(`viewer-page-${target}`);
        if (!element) return;
        programmaticScrollUntil.current = Date.now() + 900;
        // start + scroll-mt-24 keeps the cited badge visible under the header
        element.scrollIntoView({ behavior: "auto", block: "start" });
        // verify once after layout settles; re-jump if content shifted
        window.setTimeout(() => {
          const rect = element.getBoundingClientRect();
          if (rect.top >= window.innerHeight || rect.bottom <= 0) {
            programmaticScrollUntil.current = Date.now() + 900;
            element.scrollIntoView({ behavior: "auto", block: "start" });
          }
        }, 500);
      };
      const attempt = () => {
        const wrappers = Array.from(
          document.querySelectorAll<HTMLElement>("[data-page-no]"),
        );
        const ready =
          wrappers.length > 0 &&
          wrappers.every((wrapper) => wrapper.clientHeight > 100);
        if (ready || Date.now() - startedAt > 5000) {
          jump();
          return;
        }
        requestAnimationFrame(attempt);
      };
      attempt();
    });
  }, [numPages, citedPage, mounted]);

  /* keep the selector input in sync while scrolling */
  useEffect(() => {
    setDraft(String(currentPage));
  }, [currentPage]);

  const goToPage = useCallback(
    (value: number) => {
      if (!numPages) return;
      const target = Math.min(Math.max(1, value), numPages);
      setMounted((previous) => {
        const next = new Set(previous);
        for (let page = Math.max(1, target - 1); page <= Math.min(numPages, target + 1); page += 1) {
          next.add(page);
        }
        return next;
      });
      programmaticScrollUntil.current = Date.now() + 700;
      setCurrentPage(target);
      setDraft(String(target));
      requestAnimationFrame(() => {
        pageRefs.current
          .get(target)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    },
    [numPages],
  );

  if (metaError) {
    return <ViewerError status={metaError.status} />;
  }
  if (!meta) {
    return <ViewerLoading />;
  }

  const header = (
    <header
      data-testid="viewer-header"
      className="sticky top-0 z-20 border-b border-border bg-background/85 backdrop-blur"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2.5 sm:px-5">
        <div className="flex min-w-0 flex-1 basis-56 items-center gap-2">
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={backHref} aria-label="Back" data-testid="viewer-back" />}
            nativeButton={false}
            className="text-muted-foreground"
          >
            <ArrowLeft />
          </Button>
          <OrbitMark className="size-5 shrink-0 text-primary" />
          <div className="min-w-0">
            <p
              className="truncate text-sm font-semibold"
              data-testid="viewer-filename"
            >
              {meta.original_filename}
            </p>
            <p className="truncate text-[0.7rem] text-muted-foreground">
              {formatBytes(meta.file_size)} ·{" "}
              {meta.folder_name ?? "Unfiled"} · {meta.status}
            </p>
          </div>
        </div>

        {isPdf && numPages > 0 && (
          <div
            className="flex items-center gap-0.5 rounded-lg border border-border bg-muted/40 p-1"
            data-testid="page-selector"
          >
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              data-testid="page-prev"
            >
              <ChevronLeft />
            </Button>
            <input
              value={draft}
              onChange={(event) => {
                const cleaned = event.target.value
                  .replace(/[^0-9]/g, "")
                  .slice(0, 4);
                setDraft(cleaned);
                const parsed = Number.parseInt(cleaned, 10);
                if (Number.isFinite(parsed) && cleaned !== "") {
                  goToPage(parsed);
                }
              }}
              onBlur={() => setDraft(String(currentPage))}
              inputMode="numeric"
              aria-label="Page number"
              data-testid="page-input"
              className="w-10 rounded-md border border-border bg-background px-1 py-0.5 text-center text-xs tabular-nums outline-none focus:ring-2 focus:ring-ring"
            />
            <span
              className="px-1 text-xs text-muted-foreground tabular-nums"
              data-testid="page-total"
            >
              / {numPages}
            </span>
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= numPages}
              aria-label="Next page"
              data-testid="page-next"
            >
              <ChevronRight />
            </Button>
          </div>
        )}

        <Button
          variant="outline"
          size="sm"
          render={
            <a
              href={fileUrl}
              download={meta.original_filename}
              rel="noopener noreferrer"
              data-testid="download-file"
            />
          }
          nativeButton={false}
        >
          <Download />
          <span className="hidden sm:inline">Download</span>
        </Button>
      </div>
    </header>
  );

  if (fileError && !isPdf) {
    return (
      <div className="flex min-h-screen flex-col bg-background">
        {header}
        <ViewerError status={0} filename={meta.original_filename} />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {header}

      {isPdf && (
        <main
          ref={mainRef}
          className="mx-auto w-full max-w-6xl flex-1 px-3 py-7 sm:px-6"
        >
          <Document
            file={pdfFile}
            onLoadSuccess={(pdf) => {
              setNumPages(pdf.numPages);
              setFileError(null);
            }}
            onLoadError={() => setFileError("The PDF could not be loaded.")}
            onSourceError={() => setFileError("The PDF could not be loaded.")}
            loading={
              <div className="mx-auto max-w-3xl space-y-4">
                <div
                  className="w-full animate-pulse rounded-lg border border-border bg-muted/30"
                  style={{ aspectRatio: "8.5 / 11" }}
                />
              </div>
            }
            error={
              <div
                className="mx-auto max-w-md space-y-3 rounded-2xl border border-border bg-card p-8 text-center"
                data-testid="viewer-error"
              >
                <AlertTriangle className="mx-auto size-10 text-amber-500" />
                <h1 className="text-lg font-semibold">The PDF could not be loaded</h1>
                <p className="text-sm text-muted-foreground">
                  {fileError ?? "Something went wrong while rendering this file."}
                </p>
                <Button
                  render={
                    <a href={fileUrl} download={meta.original_filename} />
                  }
                  nativeButton={false}
                  variant="outline"
                >
                  <Download /> Download instead
                </Button>
              </div>
            }
            className="mx-auto flex w-full max-w-4xl flex-col items-center gap-7"
          >
            {Array.from({ length: numPages }, (_, index) => index + 1).map(
              (pageNo) => {
                const cited = citedPage === pageNo;
                return (
                  <div
                    key={pageNo}
                    id={`viewer-page-${pageNo}`}
                    data-page-no={pageNo}
                    data-testid={`viewer-page-${pageNo}`}
                    ref={(element) => {
                      if (element) {
                        pageRefs.current.set(pageNo, element);
                      } else {
                        pageRefs.current.delete(pageNo);
                      }
                    }}
                    className={cn(
                      "relative w-full scroll-mt-24 rounded-lg",
                      cited &&
                        "ring-2 ring-amber-400/90 shadow-[0_0_28px_rgba(251,191,36,0.22)]",
                    )}
                  >
                    {cited && (
                      <span
                        data-testid="cited-badge"
                        className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full border border-amber-500/40 bg-amber-500/15 px-2 py-0.5 text-[0.65rem] font-semibold text-amber-600 dark:text-amber-400"
                      >
                        Cited page
                      </span>
                    )}
                    {mounted.has(pageNo) ? (
                      <Page
                        pageNumber={pageNo}
                        width={pageWidth}
                        className="overflow-hidden rounded-lg bg-white"
                      />
                    ) : (
                      <div
                        className="w-full animate-pulse rounded-lg border border-border bg-muted/30"
                        style={{ aspectRatio: "8.5 / 11" }}
                        aria-hidden
                      />
                    )}
                  </div>
                );
              },
            )}
          </Document>
        </main>
      )}

      {meta && !isPdf && isText && textBody !== null && (
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-7">
          <pre
            data-testid="text-preview"
            className="overflow-x-auto rounded-xl border border-border bg-card p-6 font-mono text-sm leading-relaxed whitespace-pre-wrap text-foreground/90"
          >
            {textBody}
          </pre>
        </main>
      )}

      {meta && !isPdf && isText && textBody === null && !fileError && (
        <div className="flex flex-1 items-center justify-center gap-2 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="text-sm">Loading preview…</span>
        </div>
      )}

      {meta && !isPdf && !isText && (
        <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-7">
          <div
            className="mx-auto flex max-w-md flex-col items-center gap-3 rounded-2xl border border-border bg-card p-10 text-center"
            data-testid="unsupported-preview"
          >
            <FileText className="size-9 text-muted-foreground" />
            <h1 className="font-semibold">Preview not available</h1>
            <p className="text-sm text-muted-foreground">
              In-browser preview supports PDF and text files. Download{" "}
              {meta.original_filename} to open it in a native application.
            </p>
            <Button
              render={
                <a href={fileUrl} download={meta.original_filename} />
              }
              nativeButton={false}
              variant="outline"
              data-testid="download-file"
            >
              <Download /> Download file
            </Button>
          </div>
        </main>
      )}
    </div>
  );
}
