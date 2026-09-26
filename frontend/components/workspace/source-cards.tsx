"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import { cn } from "cn";

import type { ChatSource } from "@/lib/api";
import { viewerHref } from "@/lib/api";

interface SourceCardsProps {
  sources: ChatSource[];
}

function RelevanceBadge({
  score,
  rank,
}: {
  score: number | null | undefined;
  rank: number;
}) {
  if (typeof score === "number") {
    const percent = Math.round(score * 100);
    const tone =
      percent >= 80
        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
        : percent >= 50
          ? "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
          : "border-border bg-muted/60 text-muted-foreground";
    return (
      <span
        data-testid="relevance-badge"
        title={`Relevance ${percent}%`}
        className={cn(
          "shrink-0 rounded-full border px-1.5 py-px text-[0.65rem] font-semibold tabular-nums",
          tone,
        )}
      >
        {percent}%
      </span>
    );
  }
  return (
    <span
      data-testid="relevance-badge"
      title={`Relevance rank #${rank}`}
      className="shrink-0 rounded-full border border-border bg-muted/60 px-1.5 py-px text-[0.65rem] font-semibold text-muted-foreground tabular-nums"
    >
      #{rank}
    </span>
  );
}

export function SourceCards({ sources }: SourceCardsProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <span className="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">
        Sources
      </span>
      {sources.map((source, index) => {
        const canOpenViewer = Boolean(source.document_id);
        const href = canOpenViewer
          ? viewerHref(source.document_id as string, source.page)
          : `/knowledge?q=${encodeURIComponent(source.document)}`;

        return (
          <Link
            key={`${source.document}-${source.page}-${index}`}
            href={href}
            {...(canOpenViewer
              ? { target: "_blank", rel: "noopener noreferrer" }
              : {})}
            data-testid="citation-chip"
            data-page={source.page}
            title={`Open ${source.document}, page ${source.page}`}
            className="group inline-flex max-w-72 items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/10 hover:text-foreground"
          >
            <FileText className="size-3.5 shrink-0 text-primary/80" />
            <span className="truncate font-medium text-foreground/90">
              {source.document}
            </span>
            <span className="shrink-0 text-muted-foreground/70">
              • Page {source.page}
            </span>
            <RelevanceBadge score={source.score} rank={index + 1} />
          </Link>
        );
      })}
    </div>
  );
}
