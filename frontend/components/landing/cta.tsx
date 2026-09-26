import Link from "next/link";
import { ArrowRight, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DEMO_COMPANY, DEMO_PASSWORD, DEMO_USERS, GITHUB_URL } from "@/lib/site";
import { GitHubMark } from "./logo";
import { Reveal } from "./reveal";

export function FinalCTA() {
  return (
    <section className="relative overflow-hidden py-20 md:py-28">
      <div
        aria-hidden="true"
        className="glow-ring absolute top-1/2 left-1/2 h-[420px] w-[760px] max-w-[150vw] -translate-x-1/2 -translate-y-1/2"
      />

      <div className="relative mx-auto w-full max-w-4xl px-5 text-center">
        <Reveal>
          <p className="text-xs font-medium tracking-[0.2em] text-primary uppercase">
            Get started
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            Launch the fully seeded demo
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            {DEMO_COMPANY} comes preloaded with five folders and three
            accounts. Sign in and explore the workspace, knowledge base and
            analytics dashboard in under a minute.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button
              render={<Link href="/login" />}
              nativeButton={false}
              className="h-11 gap-2 px-6 text-base"
              data-testid="final-cta-demo"
            >
              Try Live Demo
              <ArrowRight className="!size-4" />
            </Button>
            <Button
              render={
                <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" />
              }
              nativeButton={false}
              variant="outline"
              className="h-11 gap-2 px-6 text-base"
            >
              <GitHubMark className="!size-4" />
              View GitHub
            </Button>
          </div>

          <div
            data-testid="demo-credentials"
            className="glass-card mx-auto mt-10 max-w-md rounded-2xl border border-border/70 p-5 text-left"
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                Demo credentials
              </p>
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <Copy className="size-3.5" />
                one password
              </span>
            </div>
            <ul className="mt-3 flex flex-col gap-2">
              {DEMO_USERS.map((user) => (
                <li
                  key={user.email}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/50 px-3 py-2"
                >
                  <code className="text-xs">{user.email}</code>
                  <span className="text-[11px] text-muted-foreground">
                    {user.role}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-muted-foreground">
              Password for all accounts:{" "}
              <code className="rounded bg-muted/60 px-1.5 py-0.5 text-foreground">
                {DEMO_PASSWORD}
              </code>
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
