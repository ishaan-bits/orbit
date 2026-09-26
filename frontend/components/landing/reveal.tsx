"use client";

import { motion } from "framer-motion";

import { cn } from "cn";

/** Fade-up-on-scroll wrapper (Framer Motion `whileInView`, reduced-motion safe via `MotionProvider`). */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px 0px -32px 0px" }}
      transition={{ duration: 0.6, ease: "easeOut", delay: delay / 1000 }}
      className={cn(className)}
    >
      {children}
    </motion.div>
  );
}
