"use client";

import { useCallback, useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
}

interface Profile {
  user_id: string;
  guild_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  joined_at: string;
  message_count: number;
  personality_summary: string;
  interests: string;
  notes: string;
  last_seen: string;
}

interface MemoryMessage {
  id: number;
  channel_name: string;
  content: string;
  timestamp: string;
  username: string;
}

export default function ProfilesPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [guildId, setGuildId] = useState("");
  const [search, setSearch] = useState("");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Profile | null>(null);
  const [messages, setMessages] = useState<MemoryMessage[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length) {
          setGuilds(data);
          setGuildId((prev) => prev || data[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const loadProfiles = useCallback(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    if (guildId) params.set("guildId", guildId);
    if (search.trim()) params.set("q", search.trim());
    fetch(`/api/profiles?${params}`)
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.error || "Failed to load profiles");
        setProfiles(Array.isArray(data.profiles) ? data.profiles : []);
        setTotal(data.total ?? 0);
      })
      .catch((e: Error) => {
        setError(e.message);
        setProfiles([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }, [guildId, search]);

  useEffect(() => {
    const t = setTimeout(loadProfiles, 200);
    return () => clearTimeout(t);
  }, [loadProfiles]);

  async function openProfile(p: Profile) {
    setSelected(p);
    setDetailLoading(true);
    setMessages([]);
    try {
      const res = await fetch(`/api/profiles/${p.guild_id}/${p.user_id}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to load detail");
      if (data.profile) setSelected(data.profile);
      setMessages(Array.isArray(data.messages) ? data.messages : []);
    } catch {
      setMessages([]);
    } finally {
      setDetailLoading(false);
    }
  }

  const guildName = guilds.find((g) => g.id === guildId)?.name || guildId;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
              🧠 Profiles
            </h1>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              What Jamie remembers — personality, notes, message memory
              {total ? ` · ${total} tracked` : ""}
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <select
              className="select"
              style={{ width: 200 }}
              value={guildId}
              onChange={(e) => {
                setGuildId(e.target.value);
                setSelected(null);
              }}
            >
              <option value="">All guilds in DB</option>
              {guilds.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
            <input
              className="input"
              style={{ width: 220 }}
              placeholder="Search name, notes…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <div className="card mb-4" style={{ borderColor: "rgba(240,71,71,0.4)" }}>
            <p style={{ color: "var(--danger)" }}>{error}</p>
            <p className="text-xs mt-2" style={{ color: "var(--faint)" }}>
              Profiles come from the bot SQLite DB (
              <code>Jamie/data/jamie.db</code>). Run Jamie in Discord and let
              people chat so memory fills in.
            </p>
          </div>
        )}

        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: selected
              ? "minmax(280px, 1fr) minmax(320px, 1.2fr)"
              : "1fr",
          }}
        >
          {/* List */}
          <div className="card">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-3"
              style={{ color: "var(--faint)" }}
            >
              Members {guildName ? `· ${guildName}` : ""}
            </div>

            {loading ? (
              <p style={{ color: "var(--faint)" }}>Loading memory…</p>
            ) : profiles.length === 0 ? (
              <p style={{ color: "var(--faint)" }}>
                No profiles yet. Once Jamie is online and people talk, they show
                up here.
              </p>
            ) : (
              <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-1">
                {profiles.map((p) => {
                  const active =
                    selected?.user_id === p.user_id &&
                    selected?.guild_id === p.guild_id;
                  return (
                    <button
                      key={`${p.guild_id}-${p.user_id}`}
                      type="button"
                      onClick={() => openProfile(p)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all"
                      style={{
                        background: active
                          ? "var(--primary-dim)"
                          : "var(--surface)",
                        border: active
                          ? "1px solid rgba(57,183,196,0.35)"
                          : "1px solid var(--line)",
                      }}
                    >
                      {p.avatar_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={p.avatar_url}
                          alt=""
                          className="w-9 h-9 rounded-full object-cover"
                        />
                      ) : (
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
                          style={{
                            background: "var(--primary-dim)",
                            color: "var(--primary)",
                          }}
                        >
                          {(p.display_name || p.username || "?").charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <div
                          className="font-semibold text-sm truncate"
                          style={{ color: "var(--text)" }}
                        >
                          {p.display_name || p.username || p.user_id}
                        </div>
                        <div className="text-xs truncate" style={{ color: "var(--faint)" }}>
                          @{p.username || "unknown"} · {p.message_count} msgs
                          {p.personality_summary ? " · profiled" : ""}
                        </div>
                      </div>
                      <span style={{ color: "var(--faint)" }}>→</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Detail */}
          {selected && (
            <div className="card animate-fade space-y-4">
              <div className="flex items-start gap-3">
                {selected.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={selected.avatar_url}
                    alt=""
                    className="w-14 h-14 rounded-full object-cover"
                  />
                ) : (
                  <div
                    className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold"
                    style={{
                      background: "var(--primary-dim)",
                      color: "var(--primary)",
                    }}
                  >
                    {(selected.display_name || "?").charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1">
                  <h2 className="text-lg font-bold" style={{ color: "var(--text)" }}>
                    {selected.display_name || selected.username}
                  </h2>
                  <p className="text-sm" style={{ color: "var(--muted)" }}>
                    @{selected.username || "—"} · ID{" "}
                    <code style={{ color: "var(--faint)" }}>{selected.user_id}</code>
                  </p>
                  <p className="text-xs mt-1" style={{ color: "var(--faint)" }}>
                    {selected.message_count} messages memorized
                    {selected.last_seen
                      ? ` · last seen ${selected.last_seen.slice(0, 16).replace("T", " ")}`
                      : ""}
                    {selected.joined_at
                      ? ` · joined ${selected.joined_at.slice(0, 10)}`
                      : ""}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ fontSize: "0.75rem" }}
                  onClick={() => setSelected(null)}
                >
                  ✕
                </button>
              </div>

              <section>
                <div
                  className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--faint)" }}
                >
                  Personality
                </div>
                <p className="text-sm" style={{ color: "var(--text)" }}>
                  {selected.personality_summary || (
                    <span style={{ color: "var(--faint)" }}>
                      No personality summary yet (Jamie analyzes after enough
                      messages).
                    </span>
                  )}
                </p>
              </section>

              <section>
                <div
                  className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--faint)" }}
                >
                  Interests
                </div>
                <p className="text-sm" style={{ color: "var(--text)" }}>
                  {selected.interests || (
                    <span style={{ color: "var(--faint)" }}>—</span>
                  )}
                </p>
              </section>

              <section>
                <div
                  className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--faint)" }}
                >
                  Notes
                </div>
                <p
                  className="text-sm whitespace-pre-wrap"
                  style={{ color: "var(--text)" }}
                >
                  {selected.notes || (
                    <span style={{ color: "var(--faint)" }}>No notes</span>
                  )}
                </p>
              </section>

              <section>
                <div
                  className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: "var(--faint)" }}
                >
                  Recent memory
                </div>
                {detailLoading ? (
                  <p className="text-sm" style={{ color: "var(--faint)" }}>
                    Loading…
                  </p>
                ) : messages.length === 0 ? (
                  <p className="text-sm" style={{ color: "var(--faint)" }}>
                    No stored messages for this user.
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[40vh] overflow-y-auto">
                    {messages.map((m) => (
                      <div
                        key={m.id}
                        className="px-3 py-2 rounded-lg text-xs"
                        style={{
                          background: "var(--surface)",
                          border: "1px solid var(--line)",
                        }}
                      >
                        <div style={{ color: "var(--faint)" }}>
                          #{m.channel_name || "?"} ·{" "}
                          {(m.timestamp || "").slice(0, 16).replace("T", " ")}
                        </div>
                        <div
                          className="mt-1 whitespace-pre-wrap"
                          style={{ color: "var(--muted)" }}
                        >
                          {m.content}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}
        </div>
      </main>
      <JamieChat
        guildId={guildId || undefined}
        guildContext={
          selected
            ? `Viewing memory profile for ${selected.display_name || selected.username} (${selected.user_id}) in guild ${selected.guild_id}`
            : guildId
              ? `Browsing Jamie memory profiles for guild ${guildId}`
              : "Browsing Jamie memory profiles"
        }
      />
    </div>
  );
}
