import Link from "next/link";

import { GITHUB_URL } from "@/lib/site";
import { OrbitMark } from "./logo";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/workspace", label: "AI Workspace" },
      { href: "/knowledge", label: "Knowledge Base" },
      { href: "/analytics", label: "Analytics" },
      { href: "/login", label: "Sign in" },
    ],
  },
  {
    title: "Resources",
    links: [
      { href: "/api/health", label: "API health" },
      { href: "/docs", label: "API reference" },
      { href: GITHUB_URL, label: "GitHub", external: true },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer
      data-testid="site-footer"
      className="border-t border-border/60 bg-background/60"
    >
      <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-12 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Link href="/" className="flex items-center gap-2.5 font-semibold">
            <OrbitMark className="size-7 text-primary" />
            Orbit
          </Link>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted-foreground">
            The enterprise AI knowledge workspace: hybrid retrieval, cited
            answers and role-based access in one platform.
          </p>
        </div>

        {COLUMNS.map((column) => (
          <nav key={column.title} aria-label={column.title}>
            <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
              {column.title}
            </p>
            <ul className="mt-3 flex flex-col gap-2">
              {column.links.map((link) =>
                link.external ? (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-muted-foreground transition hover:text-foreground"
                    >
                      {link.label}
                    </a>
                  </li>
                ) : (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ),
              )}
            </ul>
          </nav>
        ))}
      </div>

      <div className="border-t border-border/60">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-2 px-5 py-5 text-xs text-muted-foreground sm:flex-row">
          <p>© {new Date().getFullYear()} Orbit. All rights reserved.</p>
          <p>Demo tenant: NovaTech Systems</p>
        </div>
      </div>
    </footer>
  );
}
