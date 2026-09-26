import { Database, Server, Sparkles, Waypoints, Globe } from "lucide-react";

import { Reveal } from "./reveal";

const SYSTEM_NODES = [
  { icon: Globe, title: "Browser", detail: "React 19 · dark UI" },
  { icon: Waypoints, title: "Next.js 15", detail: "Vercel · edge + /api proxy" },
  { icon: Server, title: "FastAPI", detail: "Render · REST + SSE" },
  { icon: Database, title: "SQLite + Chroma", detail: "persistent disk" },
  { icon: Sparkles, title: "Gemini", detail: "generation provider" },
];

const PIPELINE = [
  "Upload",
  "Chunk",
  "Embed",
  "Hybrid search",
  "Rerank",
  "Generate",
  "Cite",
];

export function Architecture() {
  return (
    <section id="architecture" className="scroll-mt-24 py-16 md:py-24">
      <div className="mx-auto w-full max-w-6xl px-5">
        <Reveal className="text-center">
          <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
            Architecture
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            A clean split, end to end
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-muted-foreground">
            Static frontend on Vercel, stateless API on Render, data on a
            persistent disk. The same stack runs locally with one command each.
          </p>
        </Reveal>

        <Reveal delay={100} className="mt-10">
          <div
            data-testid="architecture-diagram"
            className="rounded-2xl border border-border/60 bg-card/50 p-5 md:p-8"
          >
            <p className="text-center text-xs font-medium tracking-wider text-muted-foreground uppercase">
              System diagram
            </p>
            <div className="mt-5 flex flex-col items-stretch gap-3 md:flex-row md:items-center md:justify-between">
              {SYSTEM_NODES.map((node, index) => (
                <div key={node.title} className="contents">
                  <div className="flex-1 rounded-xl border border-border/70 bg-background/60 px-4 py-3.5 text-center">
                    <node.icon className="mx-auto size-5 text-primary" />
                    <p className="mt-2 text-sm font-medium">{node.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {node.detail}
                    </p>
                  </div>
                  {index < SYSTEM_NODES.length - 1 ? (
                    <span
                      aria-hidden="true"
                      className="shrink-0 self-center text-muted-foreground/60 max-md:rotate-90 md:text-lg"
                    >
                      →
                    </span>
                  ) : null}
                </div>
              ))}
            </div>

            <div className="my-6 h-px bg-border/60" />

            <p className="text-center text-xs font-medium tracking-wider text-muted-foreground uppercase">
              Retrieval pipeline
            </p>
            <ol className="mt-5 flex flex-wrap items-center justify-center gap-2">
              {PIPELINE.map((step, index) => (
                <li key={step} className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/60 px-3.5 py-1.5 text-xs font-medium">
                    <span className="size-5 rounded-full bg-primary/15 text-center text-[10px] leading-5 text-primary">
                      {index + 1}
                    </span>
                    {step}
                  </span>
                  {index < PIPELINE.length - 1 ? (
                    <span aria-hidden="true" className="text-muted-foreground/50">
                      →
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>

            <p className="mt-6 text-center text-xs text-muted-foreground">
              Queries are access-filtered before retrieval, so answers never
              surface documents a role cannot open.
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
