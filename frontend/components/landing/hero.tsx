"use client";

import Link from "next/link";
import { motion, type Variants } from "framer-motion";
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

const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
};

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

      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="relative mx-auto w-full max-w-6xl px-5 text-center"
      >
        <motion.span
          variants={item}
          className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground"
        >
          <span
            className="size-1.5 rounded-full bg-primary"
            style={{ animation: "orbit-pulse 2s ease-in-out infinite" }}
          />
          Enterprise AI knowledge platform
        </motion.span>

        <motion.h1
          variants={item}
          className="mx-auto mt-7 max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl md:text-6xl"
        >
          Enterprise Knowledge{" "}
          <span className="text-gradient">Operating System</span>
        </motion.h1>

        <motion.p
          variants={item}
          className="mx-auto mt-6 max-w-2xl text-pretty text-base text-muted-foreground md:text-lg"
        >
          Secure, grounded AI search across your organization&apos;s documents.
        </motion.p>

        <motion.div
          variants={item}
          className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Button
            render={<Link href="/login" />}
            nativeButton={false}
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
            nativeButton={false}
            variant="outline"
            className="h-11 gap-2 px-6 text-base"
            data-testid="hero-cta-github"
          >
            <GitHubMark className="!size-4" />
            View GitHub
          </Button>
        </motion.div>

        <motion.ul
          variants={item}
          className="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-muted-foreground"
        >
          {CHIPS.map((chip) => (
            <li key={chip.label} className="flex items-center gap-2">
              <chip.icon className="size-4 text-primary" />
              {chip.label}
            </li>
          ))}
        </motion.ul>
      </motion.div>
    </section>
  );
}
