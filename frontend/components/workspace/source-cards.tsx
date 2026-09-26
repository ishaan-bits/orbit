"use client";

import Link from "next/link";
import { FileText } from "lucide-react";

import type { ChatSource } from "@/lib/api";

interface SourceCardsProps {
  sources: ChatSource[];
}

export function SourceCards({ sources }: SourceCardsProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <span className="text-[0.7rem] font-medium tracking-wide text-muted-foreground uppercase">
        Sources
      </span>
      {sources.map((source) => (
        <Link
          key={`${source.document}-${source.page}`}
          href={`/knowledge?q=${encodeURIComponent(source.document)}`}
          className="inline-flex max-w-64 items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <FileText className="size-3.5 shrink-0" />
          <span className="truncate">{source.document}</span>
          <span className="shrink-0 text-muted-foreground/70">
            p. {source.page}
          </span>
        </Link>
      ))}
    </div>
  );
}
