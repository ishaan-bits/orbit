"use client";

import { MotionConfig } from "framer-motion";

/** Shared Framer Motion scope for the landing page (honors `prefers-reduced-motion`). */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
