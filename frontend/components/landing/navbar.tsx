"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SECTIONS } from "@/lib/site";
import { cn } from "cn";
import { OrbitMark } from "./logo";

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      data-testid="landing-navbar"
      className={cn(
        "fixed inset-x-0 top-0 z-50 border-b transition-colors duration-300",
        scrolled || open ? "glass border-border/60" : "border-transparent",
      )}
    >
      <nav className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
        <Link
          href="/"
          className="flex items-center gap-2.5 text-[15px] font-semibold tracking-tight"
        >
          <OrbitMark className="size-7 text-primary" />
          Orbit
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {SECTIONS.map((section) => (
            <a
              key={section.href}
              href={section.href}
              className="rounded-lg px-3 py-2 text-sm text-muted-foreground transition hover:bg-muted/60 hover:text-foreground"
            >
              {section.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          <Button
            render={<Link href="/login" />}
            nativeButton={false}
            variant="ghost"
            data-testid="nav-signin"
          >
            Sign in
          </Button>
          <Button
            render={<Link href="/login" />}
            nativeButton={false}
            data-testid="nav-cta-demo"
          >
            Try Live Demo
          </Button>
        </div>

        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          data-testid="nav-mobile-toggle"
          className="inline-flex size-9 items-center justify-center rounded-lg border border-border/60 text-muted-foreground transition hover:text-foreground md:hidden"
        >
          {open ? <X className="size-4.5" /> : <Menu className="size-4.5" />}
        </button>
      </nav>

      {open ? (
        <div
          data-testid="nav-mobile-menu"
          className="glass border-t border-border/60 px-5 pb-5 pt-3 md:hidden"
        >
          <div className="flex flex-col gap-1">
            {SECTIONS.map((section) => (
              <a
                key={section.href}
                href={section.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition hover:bg-muted/60 hover:text-foreground"
              >
                {section.label}
              </a>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <Button
              render={<Link href="/login" />}
              nativeButton={false}
              variant="outline"
              className="flex-1"
            >
              Sign in
            </Button>
            <Button
              render={<Link href="/login" />}
              nativeButton={false}
              className="flex-1"
            >
              Try Live Demo
            </Button>
          </div>
        </div>
      ) : null}
    </header>
  );
}
