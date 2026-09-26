"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useChartColors } from "./use-chart-colors";

function ChartTooltip(props: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number; color?: string }>;
}) {
  if (!props.active || !props.payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-md">
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

interface TopDocumentsChartProps {
  documents: { document: string; count: number }[];
}

export function TopDocumentsChart({ documents }: TopDocumentsChartProps) {
  const colors = useChartColors();

  return (
    <div className="h-72 w-full" data-testid="top-documents-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={documents}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 0, left: 4 }}
        >
          <CartesianGrid
            stroke={colors.border}
            strokeDasharray="3 3"
            horizontal={false}
          />
          <XAxis
            type="number"
            allowDecimals={false}
            tick={{ fill: colors.mutedForeground, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="document"
            width={124}
            tickFormatter={(value: string) =>
              value.length > 18 ? `${value.slice(0, 17)}…` : value
            }
            tick={{ fill: colors.mutedForeground, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ opacity: 0.15 }} />
          <Bar
            dataKey="count"
            name="Citations"
            fill={colors.chart1}
            radius={[0, 4, 4, 0]}
            barSize={18}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
