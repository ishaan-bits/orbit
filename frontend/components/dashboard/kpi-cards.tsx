"use client";

import { FileText, Search, Timer, TrendingUp } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsOverview } from "@/lib/api";

interface KpiCardsProps {
  overview: AnalyticsOverview;
}

interface KpiProps {
  label: string;
  value: string;
  hint: string;
  testId: string;
  icon: React.ReactNode;
}

function Kpi({ label, value, hint, testId, icon }: KpiProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <span className="text-muted-foreground" aria-hidden="true">
          {icon}
        </span>
      </CardHeader>
      <CardContent>
        <p
          className="text-2xl font-semibold tracking-tight tabular-nums"
          data-testid={testId}
        >
          {value}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

export function KpiCards({ overview }: KpiCardsProps) {
  const latency =
    overview.avg_latency_ms >= 1000
      ? `${(overview.avg_latency_ms / 1000).toFixed(1)}s`
      : `${overview.avg_latency_ms}ms`;

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" data-testid="kpi-cards">
      <Kpi
        testId="kpi-total-searches"
        label="Total searches"
        value={overview.total_queries.toLocaleString()}
        hint={`${overview.unique_users} unique user${
          overview.unique_users === 1 ? "" : "s"
        }`}
        icon={<Search className="size-4" />}
      />
      <Kpi
        testId="kpi-success-rate"
        label="Success rate"
        value={`${overview.success_rate}%`}
        hint={`${overview.failed_queries} failed quer${
          overview.failed_queries === 1 ? "y" : "ies"
        }`}
        icon={<TrendingUp className="size-4" />}
      />
      <Kpi
        testId="kpi-avg-latency"
        label="Avg latency"
        value={latency}
        hint="mean per AI query"
        icon={<Timer className="size-4" />}
      />
      <Kpi
        testId="kpi-documents-retrieved"
        label="Documents retrieved"
        value={overview.retrieved_documents_total.toLocaleString()}
        hint="cited across all answers"
        icon={<FileText className="size-4" />}
      />
    </div>
  );
}
