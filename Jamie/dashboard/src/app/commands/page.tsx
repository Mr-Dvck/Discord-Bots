"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";
import {
  COMMAND_PACKS,
  SLASH_COMMANDS,
  commandsByPack,
} from "@/lib/commands";

interface Guild {
  id: string;
  name: string;
}

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
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState("");
  const [search, setSearch] = useState("");
  const [pack, setPack] = useState<string>("All");
  const [cmdConfig, setCmdConfig] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const byPack = useMemo(() => commandsByPack(), []);

  // Fetch servers list on mount
  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setGuilds(data);
          if (data.length === 1) setSelectedGuild(data[0].id);
        }
      })
      .catch(() => {});
  }, []);

  // Load command configurations for selected server
  const loadCommands = useCallback(async (guildId: string) => {
    if (!guildId) return;
    setStatusMsg("");
    try {
      const res = await fetch(`/api/commands?guildId=${encodeURIComponent(guildId)}`);
      const data = await res.json();
      if (data.config) {
        setCmdConfig(data.config);
      } else {
        setCmdConfig({});
      }
    } catch (e: unknown) {
      setStatusMsg(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    if (selectedGuild) loadCommands(selectedGuild);
  }, [selectedGuild, loadCommands]);

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

  // Toggle command local checkbox state
  function toggleCommand(name: string) {
    const key = name.toLowerCase();
    setCmdConfig((prev) => ({
      ...prev,
      [key]: prev[key] === false ? true : false,
    }));
  }

  // Save commands configuration to the database
  async function saveCommands() {
    if (!selectedGuild) {
      setStatusMsg("Select a server first.");
      return;
    }
    setSaving(true);
    setStatusMsg("");
    try {
      const res = await fetch("/api/commands", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guildId: selectedGuild,
          config: cmdConfig,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Save failed");
      setStatusMsg("Command preferences saved successfully.");
    } catch (e: unknown) {
      setStatusMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        {/* Top Header & Server Selector */}
        <div className="flex flex-wrap items-center justify-between gap-6 mb-8 pb-6" style={{ borderBottom: "1px solid var(--line)" }}>
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
              ⌨️ Commands Manager
            </h1>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Enable or disable commands to clean up what is authorized on your server.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              className="select"
              value={selectedGuild}
              onChange={(e) => setSelectedGuild(e.target.value)}
              style={{ minWidth: 200 }}
            >
              <option value="">Select Server…</option>
              {guilds.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>

            <button
              onClick={saveCommands}
              className="btn btn-accent"
              disabled={saving || !selectedGuild}
              style={{ padding: "8px 16px" }}
            >
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>

        {/* Alerts / Success Message */}
        {statusMsg && (
          <div
            className="p-3 mb-6 rounded-lg text-sm flex items-center justify-between animate-fade"
            style={{
              background: statusMsg.includes("success") || statusMsg.includes("successfully")
                ? "rgba(125,211,167,0.15)"
                : "rgba(240,71,71,0.15)",
              color: statusMsg.includes("success") || statusMsg.includes("successfully")
                ? "var(--ok)"
                : "var(--danger)",
              border: `1px solid ${
                statusMsg.includes("success") || statusMsg.includes("successfully")
                  ? "rgba(125,211,167,0.3)"
                  : "rgba(240,71,71,0.3)"
              }`,
            }}
          >
            <span>{statusMsg}</span>
            <button onClick={() => setStatusMsg("")} className="text-xs hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {/* Search & Packs Filters */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex gap-2 flex-wrap">
            {["All", ...COMMAND_PACKS].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPack(p)}
                className="btn"
                style={{
                  background: pack === p ? "var(--primary-dim)" : "transparent",
                  color: pack === p ? "var(--primary)" : "var(--muted)",
                  border: pack === p ? "1px solid rgba(57,183,196,0.3)" : "1px solid var(--line)",
                  fontSize: "0.8rem",
                  padding: "6px 12px",
                }}
              >
                {p}
              </button>
            ))}
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

        {/* Command list */}
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

                  <div className="grid gap-2">
                    {cmds.map((c) => {
                      const cmdKey = c.name.toLowerCase();
                      const isChecked = cmdConfig[cmdKey] !== false; // default enabled
                      return (
                        <label
                          key={c.full}
                          className="flex items-center gap-4 px-4 py-3 rounded-lg cursor-pointer transition-all hover:bg-[var(--line)]"
                          style={{
                            background: "var(--surface)",
                            border: "1px solid var(--line)",
                            opacity: isChecked ? 1 : 0.6,
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleCommand(c.name)}
                            className="checkbox"
                            disabled={!selectedGuild}
                          />

                          <code
                            className="text-sm font-semibold shrink-0"
                            style={{
                              color: isChecked ? "var(--primary)" : "var(--muted)",
                              background: isChecked ? "var(--primary-dim)" : "var(--line)",
                              padding: "2px 8px",
                              borderRadius: 6,
                            }}
                          >
                            {c.full}
                          </code>

                          <span
                            className="text-sm flex-1 min-w-[180px]"
                            style={{ color: isChecked ? "var(--text)" : "var(--faint)" }}
                          >
                            {c.description}
                          </span>

                          <span className="badge badge-standard">{c.category}</span>
                        </label>
                      );
                    })}
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </main>
      <JamieChat
        guildId={selectedGuild || undefined}
        guildContext={
          selectedGuild
            ? `Managing command visibility for server ${guilds.find((g) => g.id === selectedGuild)?.name} (${selectedGuild}).`
            : ""
        }
      />
    </div>
  );
}
