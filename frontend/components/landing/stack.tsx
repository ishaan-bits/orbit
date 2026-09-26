import { Reveal } from "./reveal";

const GROUPS = [
  {
    label: "Frontend",
    items: [
      "Next.js 15",
      "React 19",
      "TypeScript",
      "Tailwind CSS v4",
      "shadcn/ui",
      "Recharts",
    ],
  },
  {
    label: "Backend",
    items: [
      "FastAPI",
      "SQLAlchemy 2",
      "Alembic",
      "Pydantic Settings",
      "JWT cookies",
      "SSE streaming",
    ],
  },
  {
    label: "Data & AI",
    items: [
      "SQLite",
      "ChromaDB",
      "sentence-transformers",
      "BM25 + vectors",
      "Cross-encoder rerank",
      "Gemini",
    ],
  },
  {
    label: "Delivery",
    items: [
      "Vercel",
      "Render",
      "Alembic migrations",
      "Health checks",
      "Structured logs",
      "Env-driven config",
    ],
  },
];

export function TechStack() {
  return (
    <section id="stack" data-testid="tech-stack" className="scroll-mt-24 py-16 md:py-24">
      <div className="mx-auto w-full max-w-6xl px-5">
        <Reveal>
          <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
            Tech stack
          </p>
          <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
            Modern where it matters, boring where it counts
          </h2>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Type-safe end to end — React server components to Pydantic
            contracts — with every moving part a team you hire already knows.
          </p>
        </Reveal>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {GROUPS.map((group, index) => (
            <Reveal key={group.label} delay={index * 70}>
              <div className="glass-card h-full rounded-2xl p-5">
                <p className="text-xs font-medium tracking-[0.16em] text-primary uppercase">
                  {group.label}
                </p>
                <ul className="mt-4 flex flex-wrap gap-2">
                  {group.items.map((tech) => (
                    <li
                      key={tech}
                      className="rounded-full border border-border/60 bg-muted/40 px-2.5 py-1 font-mono text-xs text-muted-foreground"
                    >
                      {tech}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
