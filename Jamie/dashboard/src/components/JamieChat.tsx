"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export default function JamieChat({ guildContext }: { guildContext?: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Yo. I'm Jamie. What do you need? Tell me how you want the server set up and I'll make it happen.",
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  async function sendMessage() {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      role: "user",
      content: input.trim(),
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [...messages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
          context: guildContext || "",
        }),
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response,
          timestamp: Date.now(),
        },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `*[Error: ${e.message}]*`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Chat toggle button — bottom right */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center rounded-full shadow-lg transition-all hover:scale-105"
        style={{
          width: 56,
          height: 56,
          background: open ? "var(--surface2)" : "var(--primary)",
          border: open ? "1px solid var(--line)" : "1px solid var(--primary)",
          color: open ? "var(--text)" : "#0f1418",
          fontSize: "1.5rem",
          boxShadow: "0 8px 32px rgba(57,183,196,0.3)",
        }}
      >
        {open ? "✕" : "🔥"}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          className="fixed bottom-24 right-6 z-50 flex flex-col animate-slide"
          style={{
            width: 380,
            height: 520,
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "0 16px 48px rgba(0,0,0,0.4)",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-3 px-4 py-3"
            style={{
              borderBottom: "1px solid var(--line)",
              background: "var(--surface2)",
            }}
          >
            <div
              className="flex items-center justify-center rounded-lg text-sm"
              style={{
                width: 32,
                height: 32,
                background: "var(--primary-dim)",
                border: "1px solid rgba(57,183,196,0.3)",
              }}
            >
              🔥
            </div>
            <div>
              <div className="font-bold text-sm" style={{ color: "var(--primary)" }}>
                Jamie
              </div>
              <div className="text-xs" style={{ color: "var(--faint)" }}>
                Private Chat
              </div>
            </div>
            <div
              className="ml-auto w-2 h-2 rounded-full"
              style={{ background: "var(--accent)" }}
            />
          </div>

          {/* Messages */}
          <div
            className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
            style={{ background: "var(--bg)" }}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                className="flex gap-2 animate-fade"
                style={{
                  flexDirection: msg.role === "user" ? "row-reverse" : "row",
                }}
              >
                {/* Avatar */}
                <div
                  className="flex items-center justify-center rounded-full text-xs shrink-0"
                  style={{
                    width: 28,
                    height: 28,
                    background:
                      msg.role === "assistant"
                        ? "var(--primary-dim)"
                        : "var(--warn-dim)",
                    border:
                      msg.role === "assistant"
                        ? "1px solid rgba(57,183,196,0.3)"
                        : "1px solid rgba(240,179,90,0.3)",
                    color:
                      msg.role === "assistant"
                        ? "var(--primary)"
                        : "var(--warn)",
                    fontSize: "0.7rem",
                  }}
                >
                  {msg.role === "assistant" ? "🔥" : "👤"}
                </div>

                {/* Bubble */}
                <div
                  className="max-w-[75%] rounded-xl px-3 py-2 text-sm"
                  style={{
                    background:
                      msg.role === "user"
                        ? "var(--surface3)"
                        : "var(--surface2)",
                    border: "1px solid var(--line)",
                    color: "var(--text)",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-2 animate-fade">
                <div
                  className="flex items-center justify-center rounded-full text-xs shrink-0"
                  style={{
                    width: 28,
                    height: 28,
                    background: "var(--primary-dim)",
                    border: "1px solid rgba(57,183,196,0.3)",
                  }}
                >
                  🔥
                </div>
                <div
                  className="rounded-xl px-3 py-2 text-sm"
                  style={{
                    background: "var(--surface2)",
                    border: "1px solid var(--line)",
                    color: "var(--faint)",
                  }}
                >
                  <span className="animate-pulse">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div
            className="px-3 py-3"
            style={{
              borderTop: "1px solid var(--line)",
              background: "var(--surface2)",
            }}
          >
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Tell Jamie what you need..."
                className="input flex-1"
                style={{ padding: "8px 12px", fontSize: "0.85rem" }}
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="btn btn-primary"
                style={{ padding: "8px 12px" }}
              >
                ↑
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
