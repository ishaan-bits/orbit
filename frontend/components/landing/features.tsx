import { BarChart3, FileText, Quote, Search, ShieldCheck, Zap } from "lucide-react";

import { Reveal } from "./reveal";

const FEATURES = [
  {
    icon: Search,
    title: "Hybrid retrieval",
    body: "BM25 keyword search fused with vector similarity, then cross-encoded reranking — precise even on exact identifiers and jargon.",
  },
  {
    icon: Quote,
    title: "Citations on every answer",
    body: "Each response links back to the source document and page it was grounded in, so answers can be verified in one click.",
  },
  {
    icon: ShieldCheck,
    title: "Role-based access control",
    body: "Admin, HR and Engineering roles see only the folders they belong to. Permissions are enforced at the API and inside retrieval.",
  },
  {
    icon: Zap,
    title: "Streaming answers",
    body: "Token-by-token streaming over SSE keeps the workspace snappy, with structured source cards delivered before the first word.",
  },
  {
    icon: FileText,
    title: "Document pipeline",
    body: "Upload PDF, DOCX, TXT or Markdown — Orbit chunks, embeds and indexes into ChromaDB automatically, with per-document status.",
  },
  {
    icon: BarChart3,
    title: "Analytics dashboard",
    body: "Admin-only metrics for search volume, success rate, latency, top documents and recent queries across the whole company.",
  },
];

export function Features() {
  return (
    <section id="features" className="scroll-mt-24 py-16 md:py-24">
      <div className="mx-auto w-full max-w-6xl px-5">
        <Reveal>
          <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
            Enterprise features
          </p>
          <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
            Everything a knowledge team needs — nothing it doesn&apos;t
          </h2>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Built as a production SaaS: retrieval you can audit, permissions you
            can reason about, and metrics leadership actually reads.
          </p>
        </Reveal>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <Reveal key={feature.title} delay={index * 70}>
              <div className="group h-full rounded-2xl border border-border/60 bg-card/50 p-5 transition duration-300 hover:border-primary/40 hover:bg-card">
                <span className="inline-flex size-10 items-center justify-center rounded-xl bg-primary/15 text-primary transition group-hover:bg-primary group-hover:text-primary-foreground">
                  <feature.icon className="size-5" />
                </span>
                <h3 className="mt-4 text-base font-medium">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {feature.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
