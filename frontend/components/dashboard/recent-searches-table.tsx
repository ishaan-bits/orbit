"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { AnalyticsRecentSearch } from "@/lib/api";

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface RecentSearchesTableProps {
  searches: AnalyticsRecentSearch[];
}

export function RecentSearchesTable({ searches }: RecentSearchesTableProps) {
  return (
    <div data-testid="recent-searches-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Query</TableHead>
            <TableHead>Result</TableHead>
            <TableHead className="text-right">Docs</TableHead>
            <TableHead className="text-right">Latency</TableHead>
            <TableHead className="text-right">When</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {searches.map((search) => (
            <TableRow key={search.id}>
              <TableCell
                className="max-w-48 truncate font-medium"
                title={search.query}
              >
                {search.query}
              </TableCell>
              <TableCell>
                <Badge
                  variant={search.success ? "secondary" : "destructive"}
                  data-testid="search-result-badge"
                >
                  {search.success ? "Success" : "Failed"}
                </Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {search.retrieved_documents}
              </TableCell>
              <TableCell className="text-right tabular-nums text-muted-foreground">
                {search.latency_ms}ms
              </TableCell>
              <TableCell className="text-right whitespace-nowrap text-muted-foreground">
                {formatWhen(search.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
