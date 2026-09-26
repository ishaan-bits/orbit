"use client";

import { MessageSquareText } from "lucide-react";

const STARTER_QUESTIONS = [
  "What is our vacation policy?",
  "How do I request time off?",
  "Summarise the employee handbook",
  "What expenses are reimbursable?",
];

interface StarterQuestionsProps {
  disabled?: boolean;
  onPick: (question: string) => void;
}

export function StarterQuestions({
  disabled = false,
  onPick,
}: StarterQuestionsProps) {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-6 text-center sm:px-6">
      <span className="mx-auto flex size-12 items-center justify-center rounded-2xl border border-border bg-muted text-muted-foreground">
        <MessageSquareText className="size-6" />
      </span>
      <h2 className="mt-4 text-lg font-semibold tracking-tight">
        Ask anything about your documents
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Orbit answers only from your indexed knowledge base and cites every
        source.
      </p>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {STARTER_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            disabled={disabled}
            onClick={() => onPick(question)}
            className="rounded-xl border border-border bg-card px-4 py-3 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
