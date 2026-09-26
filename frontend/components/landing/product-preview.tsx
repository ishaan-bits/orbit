"use client";

import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  FileText,
  LayoutDashboard,
  Loader2,
  Lock,
  MessageSquareText,
  Plus,
  RefreshCw,
  Search,
  Send,
} from "lucide-react";

import { Reveal } from "./reveal";

type Tab = "workspace" | "knowledge" | "dashboard";

const TABS: { id: Tab; label: string }[] = [
  { id: "workspace", label: "Workspace" },
  { id: "knowledge", label: "Knowledge" },
  { id: "dashboard", label: "Dashboard" },
];

const DEMO_QUESTION = "What is our parental leave policy?";
const DEMO_ANSWER =
  "NovaTech grants 16 weeks of fully paid parental leave to all new parents, usable within the first 12 months of birth or adoption. Notify People Ops and your manager at least 30 days ahead — approvals are handled through the HR portal.";
const DEMO_CITATIONS = [
  { file: "employee-handbook.pdf", page: 4 },
  { file: "parental-leave.docx", page: 1 },
];

const PREVIEW_FOLDERS = [
  { name: "General", open: false },
  { name: "HR", open: false },
  { name: "Engineering", open: true },
  { name: "Product", open: false },
  { name: "Security", open: false },
  { name: "Legal", open: false },
];

const PREVIEW_FILES = [
  { name: "employee-handbook.pdf", folder: "HR", status: "Indexed" },
  { name: "parental-leave.docx", folder: "HR", status: "Indexed" },
  { name: "q3-roadmap.md", folder: "Product", status: "Indexed" },
  { name: "onboarding-guide.pdf", folder: "Engineering", status: "Indexed" },
  { name: "security-review.txt", folder: "Security", status: "Processing" },
];

const PREVIEW_KPIS = [
  { label: "Total searches", value: "1,284" },
  { label: "Success rate", value: "98.6%" },
  { label: "Avg latency", value: "742ms" },
  { label: "Docs retrieved", value: "3,140" },
];

const PREVIEW_BARS = [
  { day: "Mon", value: 62 },
  { day: "Tue", value: 78 },
  { day: "Wed", value: 54 },
  { day: "Thu", value: 88 },
  { day: "Fri", value: 96 },
  { day: "Sat", value: 34 },
  { day: "Sun", value: 41 },
];

const PREVIEW_QUERIES = [
  { query: "expense reimbursement limit", count: 7 },
  { query: "deployment runbook steps", count: 6 },
  { query: "parental leave policy", count: 5 },
];

function WorkspacePanel() {
  const [typed, setTyped] = useState("");
  const [running, setRunning] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  const done = typed.length >= DEMO_ANSWER.length;

  function runDemo() {
    if (timer.current) clearInterval(timer.current);
    setTyped("");
    setRunning(true);
    let index = 0;
    timer.current = setInterval(() => {
      index += 3;
      setTyped(DEMO_ANSWER.slice(0, index));
      if (index >= DEMO_ANSWER.length) {
        if (timer.current) clearInterval(timer.current);
        timer.current = null;
        setRunning(false);
      }
    }, 16);
  }

  return (
    <div className="flex h-full min-h-[430px]">
      <aside className="hidden w-52 shrink-0 flex-col gap-2 border-r border-border/60 p-3 sm:flex">
        <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-2 text-xs font-medium">
          <Plus className="size-3.5 text-primary" />
          New conversation
        </div>
        <p className="px-1 pt-2 text-[10px] font-medium tracking-wider text-muted-foreground uppercase">
          History
        </p>
        {["parental leave policy", "expense limits", "onboarding steps"].map(
          (title) => (
            <div
              key={title}
              className="truncate rounded-lg px-2 py-1.5 text-xs text-muted-foreground"
            >
              {title}
            </div>
          ),
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3 pb-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MessageSquareText className="size-4 text-primary" />
            AI Workspace
          </div>
          <div className="hidden items-center gap-1.5 rounded-full border border-border/60 px-2.5 py-1 text-[11px] text-muted-foreground sm:flex">
            <Lock className="size-3" />
            Admin · NovaTech Systems
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-4">
          <div className="max-w-[85%] self-end rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm text-primary-foreground">
            {DEMO_QUESTION}
          </div>

          <div className="max-w-[92%] self-start rounded-2xl rounded-bl-md bg-muted/50 px-4 py-3 text-sm leading-relaxed">
            {typed.length === 0 ? (
              <span className="text-muted-foreground">
                Run the demo query to stream a cited answer…
              </span>
            ) : (
              <>
                {typed}
                {running ? (
                  <span
                    className="ml-0.5 inline-block h-4 w-0.5 translate-y-0.5 bg-primary"
                    style={{ animation: "orbit-pulse 1s step-end infinite" }}
                  />
                ) : null}
              </>
            )}
          </div>

          {done ? (
            <div
              data-testid="preview-citations"
              className="flex flex-wrap items-center gap-2 self-start"
            >
              {DEMO_CITATIONS.map((citation) => (
                <span
                  key={citation.file}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-card/70 px-2.5 py-1.5 text-xs text-muted-foreground"
                >
                  <FileText className="size-3.5 text-primary" />
                  {citation.file}
                  <span className="text-muted-foreground/70">
                    p. {citation.page}
                  </span>
                </span>
              ))}
            </div>
          ) : null}
        </div>

        <div className="mt-4 flex items-center gap-2">
          <button
            type="button"
            onClick={runDemo}
            data-testid="preview-run-demo"
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:bg-primary/85"
          >
            <Search className="size-4" />
            {done ? "Replay demo" : running ? "Streaming…" : "Run demo query"}
          </button>
          <div className="flex h-9 flex-1 items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 text-sm text-muted-foreground">
            {DEMO_QUESTION}
            <Send className="ml-auto size-4 text-primary" />
          </div>
        </div>
      </div>
    </div>
  );
}

function KnowledgePanel() {
  return (
    <div className="flex h-full min-h-[430px]">
      <aside className="hidden w-52 shrink-0 flex-col gap-1 border-r border-border/60 p-3 sm:flex">
        <div className="flex items-center gap-2 rounded-lg bg-primary/15 px-2.5 py-2 text-xs font-medium text-primary">
          <BookOpen className="size-3.5" />
          Knowledge Base
        </div>
        {PREVIEW_FOLDERS.map((folder) => (
          <div
            key={folder.name}
            className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs text-muted-foreground"
          >
            <span className={folder.open ? "text-foreground" : undefined}>
              {folder.name}
            </span>
            {folder.open ? null : <Lock className="size-3 opacity-60" />}
          </div>
        ))}
      </aside>

      <div className="min-w-0 flex-1 p-4 sm:p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">Engineering · 5 documents</p>
          <span className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">
            Upload
          </span>
        </div>
        <div className="mt-4 overflow-hidden rounded-xl border border-border/60">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/40 text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">File</th>
                <th className="hidden px-3 py-2 font-medium sm:table-cell">
                  Folder
                </th>
                <th className="px-3 py-2 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {PREVIEW_FILES.map((file) => (
                <tr key={file.name} className="border-t border-border/50">
                  <td className="max-w-[180px] truncate px-3 py-2.5">
                    {file.name}
                  </td>
                  <td className="hidden px-3 py-2.5 text-muted-foreground sm:table-cell">
                    {file.folder}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {file.status === "Indexed" ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/60 px-2 py-0.5 text-[11px] text-muted-foreground">
                        <span className="size-1.5 rounded-full bg-primary" />
                        Indexed
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground">
                        <Loader2 className="size-3 animate-spin" />
                        Processing
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Restricted folders stay hidden — role checks run on the API, not just
          the UI.
        </p>
      </div>
    </div>
  );
}

function DashboardPanel() {
  return (
    <div className="min-h-[430px] p-4 sm:p-5">
      <div className="flex items-center gap-2 text-sm font-medium">
        <LayoutDashboard className="size-4 text-primary" />
        Analytics · last 14 days
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {PREVIEW_KPIS.map((kpi) => (
          <div key={kpi.label} className="rounded-xl border border-border/60 bg-card/60 p-3">
            <p className="text-[11px] text-muted-foreground">{kpi.label}</p>
            <p className="mt-1 text-xl font-semibold tracking-tight tabular-nums">
              {kpi.value}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-5">
        <div className="rounded-xl border border-border/60 bg-card/60 p-4 lg:col-span-3">
          <p className="text-xs text-muted-foreground">Daily searches</p>
          <div className="mt-3 flex h-32 items-end gap-2">
            {PREVIEW_BARS.map((bar) => (
              <div key={bar.day} className="flex flex-1 flex-col items-center gap-1.5">
                <div
                  className="w-full rounded-t bg-primary/80 transition-all"
                  style={{ height: `${bar.value}%` }}
                />
                <span className="text-[10px] text-muted-foreground">{bar.day}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-border/60 bg-card/60 p-4 lg:col-span-2">
          <p className="text-xs text-muted-foreground">Top queries</p>
          <ol className="mt-3 flex flex-col gap-2.5">
            {PREVIEW_QUERIES.map((item, index) => (
              <li key={item.query} className="flex items-center gap-3 text-xs">
                <span className="text-muted-foreground">{index + 1}</span>
                <span className="min-w-0 flex-1 truncate">{item.query}</span>
                <span className="rounded-md bg-muted/60 px-1.5 py-0.5 tabular-nums text-muted-foreground">
                  {item.count}
                </span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

export function ProductPreview() {
  const [tab, setTab] = useState<Tab>("workspace");

  return (
    <section id="preview" className="scroll-mt-24 py-16 md:py-24">
      <div className="mx-auto w-full max-w-6xl px-5">
        <Reveal className="text-center">
          <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
            Interactive preview
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            Take the workspace for a spin
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Click through the three core surfaces — then run a live query in the
            demo.
          </p>
        </Reveal>

        <Reveal delay={120} className="mt-10">
          <div
            data-testid="product-preview"
            className="overflow-hidden rounded-2xl border border-border/70 bg-card/70 shadow-2xl shadow-primary/5"
          >
            <div className="flex items-center gap-3 border-b border-border/60 bg-muted/30 px-4 py-2.5">
              <span className="flex gap-1.5" aria-hidden="true">
                <span className="size-2.5 rounded-full bg-muted-foreground/25" />
                <span className="size-2.5 rounded-full bg-muted-foreground/25" />
                <span className="size-2.5 rounded-full bg-muted-foreground/25" />
              </span>
              <span className="mx-auto rounded-md border border-border/60 bg-background/60 px-3 py-0.5 text-[11px] text-muted-foreground">
                orbit.app
              </span>
            </div>

            <div
              role="tablist"
              aria-label="Product surfaces"
              className="flex items-center gap-1 border-b border-border/60 px-3 py-2"
            >
              {TABS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={tab === item.id}
                  onClick={() => setTab(item.id)}
                  data-testid={`preview-tab-${item.id}`}
                  className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition ${
                    tab === item.id
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div>
              {tab === "workspace" ? <WorkspacePanel /> : null}
              {tab === "knowledge" ? <KnowledgePanel /> : null}
              {tab === "dashboard" ? <DashboardPanel /> : null}
            </div>
          </div>
        </Reveal>

        <Reveal delay={200} className="mt-5 text-center">
          <p className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <RefreshCw className="size-3.5" />
            A static preview — the live demo runs on your own seeded data.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
