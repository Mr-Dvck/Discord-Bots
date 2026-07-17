"use client";

import { useMemo, useState } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";
import {
  COMMAND_PACKS,
  SLASH_COMMANDS,
  commandsByPack,
} from "@/lib/commands";

const PACK_META: Record<
  string,
  { icon: string; blurb: string; color: string }
> = {
  Core: {
    icon: "🔥",
    blurb: "Setup, chat, images, memory",
    color: "var(--primary)",
  },
  Economy: {
    icon: "💰",
    blurb: "/economy daily · work · pay",
    color: "var(--warn)",
  },
  "Bot Info": {
    icon: "📡",
    blurb: "/bot info · stats · uptime · ping",
    color: "var(--accent)",
  },
  Manage: {
    icon: "🛠️",
    blurb: "Roles, purge, modules, giveaways",
    color: "var(--premium)",
  },
  Moderation: {
    icon: "🛡️",
    blurb: "/mod ban · kick · mute · lock…",
    color: "var(--danger)",
  },
  "Mod Logs": {
    icon: "📋",
    blurb: "Cases, warnings, staff notes",
    color: "var(--warn)",
  },
  Ranks: {
    icon: "🎭",
    blurb: "Joinable ranks + role info",
    color: "var(--primary)",
  },
  Misc: {
    icon: "✨",
    blurb: "AFK, whois, reminders, fun",
    color: "var(--accent)",
  },
};

export default function CommandsPage() {
  const [search, setSearch] = useState("");
  const [pack, setPack] = useState<string>("All");
  const byPack = useMemo(() => commandsByPack(), []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return SLASH_COMMANDS.filter((c) => {
      if (pack !== "All" && c.pack !== pack) return false;
      if (!q) return true;
      return (
        c.full.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.pack.toLowerCase().includes(q)
      );
    });
  }, [search, pack]);

  const grouped = useMemo(() => {
    const map: Record<string, typeof filtered> = {};
    for (const c of filtered) {
      if (!map[c.pack]) map[c.pack] = [];
      map[c.pack].push(c);
    }
    return map;
  }, [filtered]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
              ⌨️ Commands
            </h1>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {SLASH_COMMANDS.length} slash commands across {COMMAND_PACKS.length}{" "}
              packs — use these in Discord
            </p>
          </div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search commands…"
            className="input"
            style={{ width: 260 }}
          />
        </div>

        {/* Pack overview */}
        <div
          className="grid gap-3 mb-6"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}
        >
          {COMMAND_PACKS.map((p) => {
            const meta = PACK_META[p];
            const count = byPack[p]?.length ?? 0;
            const active = pack === p;
            return (
              <button
                key={p}
                type="button"
                onClick={() => setPack(active ? "All" : p)}
                className="card-sm text-left transition-all hover:scale-[1.02]"
                style={{
                  borderColor: active ? meta?.color : "var(--line)",
                  boxShadow: active ? `0 0 0 1px ${meta?.color}` : undefined,
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{meta?.icon}</span>
                  <span className="font-bold text-sm" style={{ color: meta?.color }}>
                    {p}
                  </span>
                  <span className="ml-auto badge badge-core">{count}</span>
                </div>
                <div className="text-xs" style={{ color: "var(--faint)" }}>
                  {meta?.blurb}
                </div>
              </button>
            );
          })}
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {["All", ...COMMAND_PACKS].map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPack(p)}
              className="btn"
              style={{
                background:
                  pack === p ? "var(--primary-dim)" : "transparent",
                color: pack === p ? "var(--primary)" : "var(--muted)",
                border:
                  pack === p
                    ? "1px solid rgba(57,183,196,0.3)"
                    : "1px solid var(--line)",
                fontSize: "0.8rem",
                padding: "6px 12px",
              }}
            >
              {p}
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          <div className="card">
            <p style={{ color: "var(--faint)" }}>No commands match your search.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([packName, cmds]) => {
              const meta = PACK_META[packName];
              return (
                <section key={packName} className="card animate-fade">
                  <div className="flex items-center gap-2 mb-4">
                    <span className="text-xl">{meta?.icon}</span>
                    <h2
                      className="text-lg font-bold"
                      style={{ color: meta?.color || "var(--text)" }}
                    >
                      {packName}
                    </h2>
                    <span className="badge badge-core">{cmds.length}</span>
                  </div>
                  <div className="space-y-2">
                    {cmds.map((c) => (
                      <div
                        key={c.full}
                        className="flex flex-wrap items-start gap-3 px-3 py-2.5 rounded-lg"
                        style={{
                          background: "var(--surface)",
                          border: "1px solid var(--line)",
                        }}
                      >
                        <code
                          className="text-sm font-semibold shrink-0"
                          style={{
                            color: "var(--primary)",
                            background: "var(--primary-dim)",
                            padding: "2px 8px",
                            borderRadius: 6,
                          }}
                        >
                          {c.full}
                        </code>
                        <span
                          className="text-sm flex-1 min-w-[180px]"
                          style={{ color: "var(--muted)" }}
                        >
                          {c.description}
                        </span>
                        <span className="badge badge-standard">{c.category}</span>
                      </div>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </main>
      <JamieChat guildContext="User is browsing the full slash command catalog on the dashboard." />
    </div>
  );
}
