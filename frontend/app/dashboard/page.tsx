"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, BarChart3, RefreshCw, ShieldAlert } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import {
  ChartCard,
  ChartEmptyState,
} from "@/components/dashboard/chart-card";
import { DailySearchesChart } from "@/components/dashboard/daily-searches-chart";
import { DashboardSkeleton } from "@/components/dashboard/dashboard-skeleton";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { RecentSearchesTable } from "@/components/dashboard/recent-searches-table";
import { TopDocumentsChart } from "@/components/dashboard/top-documents-chart";
import { TopQueriesList } from "@/components/dashboard/top-queries-list";
import { RequireAuth } from "@/components/require-auth";
import { UserMenu } from "@/components/user-menu";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  api,
  type AnalyticsDaily,
  type AnalyticsOverview,
  type AnalyticsRecent,
  type AnalyticsTopDocuments,
  type AnalyticsTopQueries,
} from "@/lib/api";

interface DashboardData {
  overview: AnalyticsOverview;
  daily: AnalyticsDaily;
  topDocuments: AnalyticsTopDocuments;
  topQueries: AnalyticsTopQueries;
  recent: AnalyticsRecent;
}

export default function DashboardPage() {
  return (
    <RequireAuth>
      <DashboardContent />
    </RequireAuth>
  );
}

function DashboardContent() {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overview, daily, topDocuments, topQueries, recent] =
        await Promise.all([
          api.analyticsOverview(),
          api.analyticsDaily(),
          api.analyticsTopDocuments(),
          api.analyticsTopQueries(),
          api.analyticsRecent(),
        ]);
      setData({ overview, daily, topDocuments, topQueries, recent });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not load analytics",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) void load();
  }, [isAdmin, load]);

  if (!isAdmin) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md" data-testid="admins-only">
          <CardHeader>
            <span className="mb-2 flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <ShieldAlert className="size-5" />
            </span>
            <CardTitle className="text-lg">Admins only</CardTitle>
            <CardDescription>
              The analytics dashboard is restricted to administrators. Your
              account has the {user?.role} role.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              render={<Link href="/workspace" />}
              variant="outline"
              className="w-full"
            >
              Back to workspace
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <BarChart3 className="size-5" />
            </span>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                Analytics
              </h1>
              <p className="text-sm text-muted-foreground">
                Enterprise insights across AI queries
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {data && !loading && !error ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => void load()}
                disabled={loading}
              >
                <RefreshCw />
                Refresh
              </Button>
            ) : null}
            <UserMenu />
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6 lg:px-8">
        {loading && !data ? (
          <DashboardSkeleton />
        ) : error ? (
          <Card data-testid="analytics-error">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <AlertTriangle className="size-4 text-destructive" />
                Could not load analytics
              </CardTitle>
              <CardDescription>{error}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" onClick={() => void load()}>
                Try again
              </Button>
            </CardContent>
          </Card>
        ) : data ? (
          <DashboardGrid data={data} />
        ) : null}
      </div>
    </main>
  );
}

function DashboardGrid({ data }: { data: DashboardData }) {
  const hasQueries = data.overview.total_queries > 0;

  return (
    <div className="flex flex-col gap-4">
      <KpiCards overview={data.overview} />

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard
          title="Daily searches"
          description="Queries per day over the last 14 days"
        >
          {hasQueries ? (
            <DailySearchesChart days={data.daily.days} />
          ) : (
            <ChartEmptyState
              title="No searches yet"
              hint="Ask a question in the AI workspace to see daily activity."
            />
          )}
        </ChartCard>
        <ChartCard
          title="Top documents"
          description="Most cited answer sources"
        >
          {data.topDocuments.documents.length > 0 ? (
            <TopDocumentsChart documents={data.topDocuments.documents} />
          ) : (
            <ChartEmptyState
              title="No citations yet"
              hint="Answers will credit the documents they cite."
            />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <ChartCard
          title="Recent AI searches"
          description="The latest queries across all users"
        >
          {data.recent.searches.length > 0 ? (
            <RecentSearchesTable searches={data.recent.searches} />
          ) : (
            <ChartEmptyState
              title="No searches yet"
              hint="Recorded queries appear here in real time."
            />
          )}
        </ChartCard>
        <ChartCard
          title="Top queries"
          description="Most frequent search terms"
        >
          {data.topQueries.queries.length > 0 ? (
            <TopQueriesList queries={data.topQueries.queries} />
          ) : (
            <ChartEmptyState
              title="No queries yet"
              hint="Frequent questions will be ranked here."
            />
          )}
        </ChartCard>
      </div>
    </div>
  );
}
