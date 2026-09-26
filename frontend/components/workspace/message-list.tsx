"use client";

import { useEffect, useRef } from "react";

import { MessageBubble } from "@/components/workspace/message-bubble";
import type { ChatMessage, ChatSource } from "@/lib/api";

interface MessageListProps {
  messages: ChatMessage[];
  streamingText: string | null;
  streamingSources: ChatSource[];
}

export function MessageList({
  messages,
  streamingText,
  streamingSources,
}: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const streaming = streamingText !== null;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streamingText]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {streaming && (
        <MessageBubble
          message={{
            id: "streaming",
            role: "assistant",
            content: streamingText,
            sources: streamingSources.length > 0 ? streamingSources : null,
            created_at: "",
          }}
          streaming={streamingText.length === 0}
        />
      )}

      <div ref={endRef} />
    </div>
  );
}
