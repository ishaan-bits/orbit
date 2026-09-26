"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { AnalyticsDailyPoint } from "@/lib/api";

import { useChartColors } from "./use-chart-colors";

function shortDate(date: string): string {
  const [, month, day] = date.split("-");
  return `${Number(month)}/${Number(day)}`;
}

function ChartTooltip(props: {
  active?: boolean;
  label?: string | number;
  payload?: Array<{
    name?: string;
    value?: number;
    color?: string;
  }>;
}) {
  if (!props.active || !props.payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-md">
      <p className="mb-1 text-xs font-medium text-muted-foreground">
        {String(props.label)}
      </p>
      {props.payload.map((entry, index) => (
        <p
          key={index}
          className="flex items-center gap-2 text-xs tabular-nums text-foreground"
        >
          <span
            className="size-2 rounded-full"
            style={{ backgroundColor: entry.color }}
            aria-hidden="true"
          />
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
}

interface DailySearchesChartProps {
  days: AnalyticsDailyPoint[];
}

export function DailySearchesChart({ days }: DailySearchesChartProps) {
  const colors = useChartColors();

  return (
    <div className="h-72 w-full" data-testid="daily-searches-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={days}
          margin={{ top: 8, right: 12, bottom: 0, left: -16 }}
        >
          <CartesianGrid
            stroke={colors.border}
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={{ fill: colors.mutedForeground, fontSize: 11 }}
            axisLine={{ stroke: colors.border }}
            tickLine={false}
            minTickGap={28}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: colors.mutedForeground, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: colors.border }} />
          <Line
            type="monotone"
            dataKey="queries"
            name="Searches"
            stroke={colors.chart1}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="successful"
            name="Successful"
            stroke={colors.chart2}
            strokeWidth={1.5}
            strokeDasharray="4 4"
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
