"use client";

import { useRef, useEffect, useState } from "react";
import {
  ChatMessage,
  SourceCitation,
  streamChat,
  SUGGESTED_PROMPTS,
} from "@/lib/api";
import { Send, Sparkles, BookOpen } from "lucide-react";
import clsx from "clsx";

interface Props {
  sessionId: string | null;
  disabled: boolean;
  initialMessages?: ChatMessage[];
}

export function ChatPanel({ sessionId, disabled, initialMessages = [] }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [pendingSources, setPendingSources] = useState<SourceCitation[]>([]);
  const [statusLabel, setStatusLabel] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  async function send(text: string) {
    if (!sessionId || !text.trim() || streaming) return;

    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setStreaming(true);
    setStreamBuffer("");
    setPendingSources([]);
    setStatusLabel("Retrieving chunks…");

    let sources: SourceCitation[] = [];
    let full = "";
    let gotError = false;

    try {
      await streamChat(sessionId, text.trim(), (ev) => {
        if (ev.type === "status") {
          setStatusLabel(
            ev.content === "generating"
              ? "Generating answer…"
              : "Retrieving chunks…"
          );
        } else if (ev.type === "sources") {
          sources = ev.content;
          setPendingSources(ev.content);
        } else if (ev.type === "token") {
          setStatusLabel(null);
          full += ev.content;
          setStreamBuffer(full);
        } else if (ev.type === "error") {
          gotError = true;
          setStatusLabel(null);
          full = ev.content;
          setStreamBuffer(full);
        } else if (ev.type === "done") {
          setStatusLabel(null);
          full = ev.content || full;
        }
      });

      const assistantContent =
        full.trim() ||
        (gotError ? "Request failed." : "No response from the model.");

      setMessages((m) => [
        ...m,
        { role: "assistant", content: assistantContent, sources },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `Something went wrong: ${e instanceof Error ? e.message : "Unknown error"}`,
        },
      ]);
    } finally {
      setStreamBuffer("");
      setPendingSources([]);
      setStatusLabel(null);
      setStreaming(false);
    }
  }

  return (
    <section className="glass rounded-2xl flex flex-col h-full min-h-[520px] border border-reach-border">
      <header className="px-5 py-4 border-b border-reach-border flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-violet-400" />
        <h2 className="font-display font-semibold text-lg">RAG Analyst</h2>
        <span className="ml-auto text-xs text-reach-muted">
          {sessionId ? "Memory on" : "Ingest videos to start"}
        </span>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-scroll">
        {messages.length === 0 && !streaming && (
          <div className="text-center py-8 text-reach-muted text-sm">
            <p className="mb-4">Ask anything about Video A vs Video B</p>
            <div className="flex flex-col gap-2 max-w-md mx-auto">
              {SUGGESTED_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  disabled={disabled}
                  onClick={() => send(p)}
                  className="text-left text-xs px-3 py-2 rounded-lg border border-reach-border hover:border-violet-500/50 hover:bg-violet-500/5 transition disabled:opacity-40"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}

        {streaming && streamBuffer && (
          <MessageBubble
            message={{
              role: "assistant",
              content: streamBuffer,
              sources: pendingSources,
            }}
            live
          />
        )}

        {streaming && statusLabel && !streamBuffer && (
          <div className="flex gap-2 text-sm text-reach-muted animate-pulse px-2">
            <span>{statusLabel}</span>
            <span className="text-violet-400">···</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form
        className="p-4 border-t border-reach-border"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={disabled || streaming}
            placeholder={
              disabled
                ? "Paste URLs and ingest first…"
                : "Ask about engagement, hooks, creators…"
            }
            className="flex-1 bg-reach-bg/80 border border-reach-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled || streaming || !input.trim()}
            className="px-4 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 hover:opacity-90 disabled:opacity-40 transition"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </section>
  );
}

function MessageBubble({
  message,
  live,
}: {
  message: ChatMessage;
  live?: boolean;
}) {
  const isUser = message.role === "user";

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={clsx(
          "max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-violet-600/30 border border-violet-500/30"
            : "bg-reach-card border border-reach-border"
        )}
      >
        <p className={clsx("whitespace-pre-wrap", live && "cursor-blink")}>
          {message.content}
        </p>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-reach-border/80">
            <p className="text-[10px] uppercase tracking-wider text-reach-muted flex items-center gap-1 mb-2">
              <BookOpen className="w-3 h-3" /> Sources
            </p>
            <ul className="space-y-1.5">
              {message.sources.map((s, i) => (
                <li
                  key={i}
                  className="text-xs text-cyan-400/90 bg-cyan-500/5 rounded px-2 py-1"
                >
                  <span className="font-semibold">
                    Video {s.video_id}, chunk {s.chunk_index}
                  </span>
                  <span className="text-reach-muted"> — </span>
                  <span className="text-reach-muted line-clamp-2">
                    {s.content_snippet}…
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
