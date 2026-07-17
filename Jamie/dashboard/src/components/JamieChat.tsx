"use client";

import { useState, useRef, useEffect } from "react";

interface PendingAction {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  summary: string;
  destructive: boolean;
}

interface ExecutedAction {
  id: string;
  tool: string;
  summary: string;
  ok: boolean;
  error?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  pending?: PendingAction[];
  executed?: ExecutedAction[];
  pendingResolved?: "confirmed" | "cancelled";
}

export default function JamieChat({
  guildContext,
  guildId,
}: {
  guildContext?: string;
  guildId?: string;
}) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Yo, Duck. Private line — it's me. Same blood, less of the public circus. Tell me what to build or burn and I'll run the bot for you. Channels and sections go Modern Bold Unicode, capital on the title (𝗠𝗮𝗶𝗻, 𝗧𝗲𝘅𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀). Nukes still need your Confirm.",
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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

    const nextHistory = [...messages, userMsg];
    setMessages(nextHistory);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "chat",
          messages: nextHistory
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({
              role: m.role,
              content: m.content,
            })),
          context: guildContext || "",
          guildId: guildId || "",
        }),
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response || "…",
          timestamp: Date.now(),
          pending: data.pending?.length ? data.pending : undefined,
          executed: data.executed?.length ? data.executed : undefined,
        },
      ]);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `*[Error: ${message}]*`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function confirmPending(messageIndex: number, actions: PendingAction[]) {
    if (loading) return;
    setLoading(true);

    try {
      const history = messages.slice(0, messageIndex + 1).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "confirm",
          actions,
          messages: history,
          context: guildContext || "",
          guildId: guildId || "",
        }),
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessages((prev) => {
        const copy = [...prev];
        if (copy[messageIndex]) {
          copy[messageIndex] = {
            ...copy[messageIndex],
            pending: undefined,
            pendingResolved: "confirmed",
            executed: data.executed?.length
              ? data.executed
              : copy[messageIndex].executed,
          };
        }
        return [
          ...copy,
          {
            role: "assistant",
            content: data.response || "Done.",
            timestamp: Date.now(),
            executed: data.executed?.length ? data.executed : undefined,
          },
        ];
      });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `*[Confirm failed: ${message}]*`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function cancelPending(messageIndex: number) {
    setMessages((prev) => {
      const copy = [...prev];
      if (copy[messageIndex]) {
        copy[messageIndex] = {
          ...copy[messageIndex],
          pending: undefined,
          pendingResolved: "cancelled",
        };
      }
      return [
        ...copy,
        {
          role: "assistant",
          content: "Cool. Scrubbed those pending moves. Nothing got deleted or bulk-built.",
          timestamp: Date.now(),
        },
      ];
    });
  }

  return (
    <>
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
        aria-label={open ? "Close Jamie chat" : "Open Jamie chat"}
      >
        {open ? "✕" : "🔥"}
      </button>

      {open && (
        <div
          className="fixed bottom-24 right-6 z-50 flex flex-col animate-slide"
          style={{
            width: 400,
            height: 560,
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "0 16px 48px rgba(0,0,0,0.4)",
            overflow: "hidden",
          }}
        >
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
                Dashboard operator
                {guildId ? " · server locked" : ""}
              </div>
            </div>
            <div
              className="ml-auto w-2 h-2 rounded-full"
              style={{ background: "var(--accent)" }}
            />
          </div>

          <div
            className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
            style={{ background: "var(--bg)" }}
          >
            {messages.map((msg, i) => (
              <div key={`${msg.timestamp}-${i}`} className="space-y-2">
                <div
                  className="flex gap-2 animate-fade"
                  style={{
                    flexDirection: msg.role === "user" ? "row-reverse" : "row",
                  }}
                >
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

                  <div
                    className="max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
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

                {msg.executed && msg.executed.length > 0 && (
                  <div
                    className="ml-9 rounded-lg px-3 py-2 text-xs space-y-1"
                    style={{
                      background: "var(--accent-dim)",
                      border: "1px solid rgba(125,211,167,0.25)",
                    }}
                  >
                    <div className="font-semibold" style={{ color: "var(--accent)" }}>
                      Ran
                    </div>
                    {msg.executed.map((ex) => (
                      <div
                        key={ex.id}
                        style={{ color: ex.ok ? "var(--muted)" : "var(--danger)" }}
                      >
                        {ex.ok ? "✓" : "✕"} {ex.summary}
                        {!ex.ok && ex.error ? ` — ${ex.error}` : ""}
                      </div>
                    ))}
                  </div>
                )}

                {msg.pending && msg.pending.length > 0 && (
                  <div
                    className="ml-9 rounded-lg px-3 py-2 text-xs space-y-2"
                    style={{
                      background: "var(--warn-dim)",
                      border: "1px solid rgba(240,179,90,0.3)",
                    }}
                  >
                    <div className="font-semibold" style={{ color: "var(--warn)" }}>
                      Needs confirmation
                    </div>
                    {msg.pending.map((p) => (
                      <div key={p.id} style={{ color: "var(--muted)" }}>
                        • {p.summary}
                      </div>
                    ))}
                    <div className="flex gap-2 pt-1">
                      <button
                        className="btn btn-primary"
                        style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                        disabled={loading}
                        onClick={() => confirmPending(i, msg.pending!)}
                      >
                        Confirm
                      </button>
                      <button
                        className="btn btn-ghost"
                        style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                        disabled={loading}
                        onClick={() => cancelPending(i)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {msg.pendingResolved === "confirmed" && (
                  <div
                    className="ml-9 text-xs"
                    style={{ color: "var(--accent)" }}
                  >
                    ✓ Confirmed
                  </div>
                )}
                {msg.pendingResolved === "cancelled" && (
                  <div
                    className="ml-9 text-xs"
                    style={{ color: "var(--faint)" }}
                  >
                    Cancelled
                  </div>
                )}
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
                  <span className="animate-pulse">Working the dashboard...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

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
                placeholder={
                  guildId
                    ? "e.g. make a #general channel..."
                    : "e.g. list my servers..."
                }
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
