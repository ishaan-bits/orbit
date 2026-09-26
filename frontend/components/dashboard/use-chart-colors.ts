"use client";

import { useEffect, useState } from "react";

export interface ChartColors {
  chart1: string;
  chart2: string;
  border: string;
  mutedForeground: string;
  foreground: string;
  primary: string;
}

const FALLBACK: ChartColors = {
  chart1: "#a1a1aa",
  chart2: "#71717a",
  border: "rgba(255,255,255,0.1)",
  mutedForeground: "#a1a1aa",
  foreground: "#fafafa",
  primary: "#e4e4e7",
};

/** Resolve dark-theme CSS tokens so Recharts matches the app palette. */
export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(FALLBACK);

  useEffect(() => {
    const css = getComputedStyle(document.documentElement);
    const read = (name: string, fallback: string) =>
      css.getPropertyValue(name).trim() || fallback;
    setColors({
      chart1: read("--chart-1", FALLBACK.chart1),
      chart2: read("--chart-2", FALLBACK.chart2),
      border: read("--border", FALLBACK.border),
      mutedForeground: read("--muted-foreground", FALLBACK.mutedForeground),
      foreground: read("--foreground", FALLBACK.foreground),
      primary: read("--primary", FALLBACK.primary),
    });
  }, []);

  return colors;
}
