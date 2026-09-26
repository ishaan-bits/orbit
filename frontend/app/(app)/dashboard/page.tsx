"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  FileText,
  FolderOpen,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const QUICK_ACTIONS = [
  {
    href: "/workspace",
    title: "AI Workspace",
    description: "Ask questions and get cited, grounded answers.",
    icon: Sparkles,
    testId: "quick-workspace",
  },
  {
    href: "/knowledge",
    title: "Knowledge Base",
    description: "Upload and organise the documents behind your answers.",
    icon: FolderOpen,
    testId: "quick-knowledge",
  },
  {
    href: "/analytics",
    title: "Analytics",
    description: "Search volume, success rate and top sources.",
    icon: BarChart3,
    adminOnly: true,
    testId: "quick-analytics",
  },
];

export default function DashboardHomePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";

  if (!user) return null;

  const firstName = (user.full_name || user.email).split(" ")[0];

  return (
    <div
      className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8"
      data-testid="dashboard-home"
    >
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold tracking-tight">
          Welcome back, {firstName}
        </h1>
        <p className="text-sm text-muted-foreground">
          Everything your team knows, one question away.
        </p>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK_ACTIONS.filter((action) => !action.adminOnly || isAdmin).map(
          (action) => {
            const Icon = action.icon;
            return (
              <Link key={action.href} href={action.href} data-testid={action.testId}>
                <Card className="h-full transition hover:border-primary/40 hover:bg-card">
                  <CardHeader>
                    <span className="mb-2 flex size-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
                      <Icon className="size-5" />
                    </span>
                    <CardTitle className="flex items-center gap-2 text-base">
                      {action.title}
                      <ArrowRight className="size-4 text-muted-foreground" />
                    </CardTitle>
                    <CardDescription>{action.description}</CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            );
          },
        )}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="size-4 text-primary" />
            Role-based by design
          </CardTitle>
          <CardDescription>
            You are signed in as{" "}
            <span className="font-medium text-foreground">{user.role}</span>.
            Orbit enforces your role on every folder — in the UI and inside
            retrieval — so answers never draw on documents you cannot open.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <FileText className="size-3.5 text-primary" />
            Cited answers
          </span>
          <span className="flex items-center gap-1.5">
            <FolderOpen className="size-3.5 text-primary" />
            Folder-level permissions
          </span>
          <span className="flex items-center gap-1.5">
            <BarChart3 className="size-3.5 text-primary" />
            Audited analytics
          </span>
        </CardContent>
      </Card>
    </div>
  );
}
