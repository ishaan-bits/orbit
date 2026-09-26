"use client";

import { Badge } from "@/components/ui/badge";

interface TopQueriesListProps {
  queries: { query: string; count: number }[];
}

export function TopQueriesList({ queries }: TopQueriesListProps) {
  return (
    <ol className="flex flex-col gap-3" data-testid="top-queries-list">
      {queries.map((item, index) => (
        <li key={item.query} className="flex items-center gap-3">
          <span className="w-4 shrink-0 text-xs text-muted-foreground tabular-nums">
            {index + 1}
          </span>
          <span
            className="min-w-0 flex-1 truncate text-sm"
            title={item.query}
          >
            {item.query}
          </span>
          <Badge variant="secondary" className="tabular-nums">
            {item.count}
          </Badge>
        </li>
      ))}
    </ol>
  );
}
