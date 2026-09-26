"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowUp,
  BookOpen,
  Loader2,
  Sparkles,
} from "lucide-react";

import { ConversationSidebar } from "@/components/workspace/conversation-sidebar";
import { MessageList } from "@/components/workspace/message-list";
import { StarterQuestions } from "@/components/workspace/starter-questions";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  streamChat,
  type ChatConversation,
  type ChatMessage,
  type ChatSource,
} from "@/lib/api";

let localId = 0;
function nextLocalId(prefix: string): string {
  localId += 1;
  return `${prefix}-local-${localId}`;
}

export function ChatWorkspace() {
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [input, setInput] = useState("");
  const [streamingText, setStreamingText] = useState<string | null>(null);
  const [streamingSources, setStreamingSources] = useState<ChatSource[]>([]);
  const [error, setError] = useState<string | null>(null);

  const streaming = streamingText !== null;
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const refreshHistory = useCallback(async (focusId: string | null) => {
    try {
      const history = await api.chatHistory();
      setConversations(history.conversations);
      if (focusId) {
        const active = history.conversations.find(
          (conversation) => conversation.id === focusId,
        );
        if (active) {
          setActiveId(active.id);
          setMessages(active.messages);
        }
      }
    } catch {
      // history is non-critical; the chat itself already worked
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const history = await api.chatHistory();
        setConversations(history.conversations);
        const latest = history.conversations[0];
        if (latest) {
          setActiveId(latest.id);
          setMessages(latest.messages);
        }
      } catch {
        // history is non-critical; chat still works without it
      } finally {
        setHistoryLoading(false);
      }
    })();
  }, []);

  const selectConversation = useCallback(
    (conversation: ChatConversation) => {
      if (streaming) return;
      setActiveId(conversation.id);
      setMessages(conversation.messages);
      setError(null);
      textareaRef.current?.focus();
    },
    [streaming],
  );

  const newChat = useCallback(() => {
    if (streaming) return;
    setActiveId(null);
    setMessages([]);
    setError(null);
    textareaRef.current?.focus();
  }, [streaming]);

  const send = useCallback(
    async (rawQuery: string) => {
      const query = rawQuery.trim();
      if (!query || streaming) return;

      setInput("");
      setError(null);
      setMessages((prev) => [
        ...prev,
        {
          id: nextLocalId("user"),
          role: "user",
          content: query,
          sources: null,
          created_at: new Date().toISOString(),
        },
      ]);
      setStreamingText("");
      setStreamingSources([]);

      let accumulated = "";
      let sources: ChatSource[] = [];
      let conversationId = activeId;

      await streamChat(query, activeId, {
        onSources: (received, id) => {
          sources = received;
          setStreamingSources(received);
          if (id) {
            conversationId = id;
            if (!activeId) setActiveId(id);
          }
        },
        onToken: (token) => {
          accumulated += token;
          setStreamingText(accumulated);
        },
        onDone: (result) => {
          setStreamingText(null);
          setStreamingSources([]);
          setMessages((prev) => [
            ...prev,
            {
              id: nextLocalId("assistant"),
              role: "assistant",
              content: result.answer,
              sources: result.sources,
              created_at: new Date().toISOString(),
            },
          ]);
          setActiveId(result.conversation_id);
          void refreshHistory(result.conversation_id);
        },
        onError: (message) => {
          setStreamingText(null);
          setStreamingSources([]);
          setError(message);
          if (accumulated) {
            setMessages((prev) => [
              ...prev,
              {
                id: nextLocalId("assistant"),
                role: "assistant",
                content: accumulated,
                sources: sources.length > 0 ? sources : null,
                created_at: new Date().toISOString(),
              },
            ]);
          }
          if (conversationId) {
            setActiveId(conversationId);
            void refreshHistory(conversationId);
          } else {
            void refreshHistory(null);
          }
        },
      });
    },
    [activeId, refreshHistory, streaming],
  );

  const busy = streaming;
  const empty = messages.length === 0 && !streaming;

  return (
    <div className="flex h-full min-h-0">
      <aside className="hidden w-64 shrink-0 border-r border-border md:block">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeId}
          loading={historyLoading}
          disabled={busy}
          onSelect={selectConversation}
          onNewChat={newChat}
        />
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3 md:hidden">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="size-4" />
            </span>
            <div>
              <h1 className="text-sm font-semibold tracking-tight">
                AI Workspace
              </h1>
              <p className="text-[0.7rem] text-muted-foreground">
                Grounded in your knowledge base
              </p>
            </div>
          </div>
          <div className="hidden items-center gap-3 md:flex">
            <div>
              <h1 className="text-sm font-semibold tracking-tight">
                {activeId
                  ? (conversations.find((c) => c.id === activeId)?.title ??
                    "Conversation")
                  : "New conversation"}
              </h1>
              <p className="text-[0.7rem] text-muted-foreground">
                Grounded in your knowledge base
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="md:hidden"
              onClick={() => {
                window.location.href = "/knowledge";
              }}
            >
              <BookOpen />
              Knowledge
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden"
              onClick={newChat}
              disabled={busy}
            >
              New chat
            </Button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto">
          {empty ? (
            <StarterQuestions disabled={busy} onPick={(q) => void send(q)} />
          ) : (
            <MessageList
              messages={messages}
              streamingText={streamingText}
              streamingSources={streamingSources}
            />
          )}
        </div>

        {error && (
          <div className="mx-auto w-full max-w-3xl px-4 pb-2 sm:px-6">
            <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span className="min-w-0 break-words">{error}</span>
            </div>
          </div>
        )}

        <div className="border-t border-border px-4 py-4 sm:px-6">
          <form
            className="mx-auto flex w-full max-w-3xl items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              void send(input);
            }}
          >
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void send(input);
                }
              }}
              placeholder={
                streaming ? "Orbit is answering…" : "Ask your knowledge base…"
              }
              aria-label="Ask a question"
              rows={1}
              maxLength={4000}
              className="max-h-40 min-h-10 flex-1 py-2.5"
            />
            <Button
              type="submit"
              size="icon"
              aria-label="Send message"
              disabled={busy || input.trim().length === 0}
              className="mb-0.5 size-9"
            >
              {busy ? (
                <Loader2 className="animate-spin" />
              ) : (
                <ArrowUp />
              )}
            </Button>
          </form>
          <p className="mx-auto mt-2 max-w-3xl text-[0.7rem] text-muted-foreground">
            Enter to send · Shift + Enter for a new line · Answers cite their
            sources
          </p>
        </div>
      </main>
    </div>
  );
}
