import Link from "next/link";
import { ArrowRight, BarChart3, Quote, Search, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { GITHUB_URL } from "@/lib/site";
import { GitHubMark } from "./logo";

const CHIPS = [
  { icon: Search, label: "Hybrid retrieval" },
  { icon: Quote, label: "Citations on every answer" },
  { icon: ShieldCheck, label: "Folder-level RBAC" },
  { icon: BarChart3, label: "Analytics dashboard" },
];

export function Hero() {
  return (
    <section
      data-testid="hero"
      className="relative overflow-hidden pt-32 pb-20 md:pt-44 md:pb-28"
    >
      <div aria-hidden="true" className="landing-grid absolute inset-0" />
      <div
        aria-hidden="true"
        className="glow-ring absolute -top-52 left-1/2 h-[560px] w-[900px] max-w-[160vw] -translate-x-1/2"
      />

      <div className="relative mx-auto w-full max-w-6xl px-5 text-center">
        <span className="animate-fade-up inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground">
          <span
            className="size-1.5 rounded-full bg-primary"
            style={{ animation: "orbit-pulse 2s ease-in-out infinite" }}
          />
          Enterprise AI knowledge platform
        </span>

        <h1
          className="animate-fade-up mx-auto mt-7 max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl"
          style={{ animationDelay: "80ms" }}
        >
          Ask your company anything.
          <br />
          <span className="text-gradient">Get answers you can verify.</span>
        </h1>

        <p
          className="animate-fade-up mx-auto mt-6 max-w-2xl text-pretty text-base text-muted-foreground md:text-lg"
          style={{ animationDelay: "160ms" }}
        >
          Orbit indexes your documents, retrieves the right passages with hybrid
          search, and streams cited answers — behind role-based access controls
          your security team can audit.
        </p>

        <div
          className="animate-fade-up mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
          style={{ animationDelay: "240ms" }}
        >
          <Button
            render={<Link href="/login" />}
            className="h-11 gap-2 px-6 text-base"
            data-testid="hero-cta-demo"
          >
            Try Live Demo
            <ArrowRight className="!size-4" />
          </Button>
          <Button
            render={
              <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" />
            }
            variant="outline"
            className="h-11 gap-2 px-6 text-base"
            data-testid="hero-cta-github"
          >
            <GitHubMark className="!size-4" />
            View GitHub
          </Button>
        </div>

        <ul
          className="animate-fade-up mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-muted-foreground"
          style={{ animationDelay: "320ms" }}
        >
          {CHIPS.map((chip) => (
            <li key={chip.label} className="flex items-center gap-2">
              <chip.icon className="size-4 text-primary" />
              {chip.label}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
