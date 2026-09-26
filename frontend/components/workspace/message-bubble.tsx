"use client";

import ReactMarkdown from "react-markdown";
import { Bot, User } from "lucide-react";

import { SourceCards } from "@/components/workspace/source-cards";
import type { ChatMessage } from "@/lib/api";
import { cn } from "cn";

export function TypingDots() {
  return (
    <span
      className="inline-flex items-center gap-1 py-1"
      aria-label="Orbit is thinking"
    >
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="size-1.5 animate-bounce rounded-full bg-muted-foreground"
          style={{
            animationDelay: `${index * 0.15}s`,
            animationDuration: "1s",
          }}
        />
      ))}
    </span>
  );
}

interface MessageBubbleProps {
  message: ChatMessage;
  streaming?: boolean;
}

export function MessageBubble({ message, streaming = false }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <span
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border border-border bg-muted text-muted-foreground",
        )}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </span>

      <div
        className={cn(
          "min-w-0 rounded-2xl px-4 py-3",
          isUser
            ? "max-w-[80%] bg-primary text-primary-foreground"
            : "max-w-[46rem] border border-border bg-card",
        )}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <>
            {message.content ? (
              <div className="text-sm break-words [&_a]:text-primary [&_a]:underline [&_a]:underline-offset-2 [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-xs [&_h1]:mt-3 [&_h1]:text-base [&_h1]:font-semibold [&_h1:first-child]:mt-0 [&_h2]:mt-3 [&_h2]:text-sm [&_h2]:font-semibold [&_h2:first-child]:mt-0 [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_ol>li]:marker:text-muted-foreground [&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-3 [&_strong]:font-semibold [&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-medium [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ul>li]:marker:text-muted-foreground">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            ) : streaming ? (
              <TypingDots />
            ) : null}

            {message.sources && message.sources.length > 0 && (
              <SourceCards sources={message.sources} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
