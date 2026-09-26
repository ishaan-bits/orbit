"use client";

import type { ReactNode } from "react";
import { BarChart3 } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ChartCardProps {
  title: string;
  description?: string;
  children: ReactNode;
}

export function ChartCard({ title, description, children }: ChartCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

interface EmptyStateProps {
  title: string;
  hint?: string;
}

export function ChartEmptyState({ title, hint }: EmptyStateProps) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <BarChart3 className="size-5" />
      </span>
      <p className="text-sm font-medium">{title}</p>
      {hint ? (
        <p className="max-w-60 text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}
