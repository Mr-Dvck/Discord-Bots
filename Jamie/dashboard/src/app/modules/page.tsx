"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
}

interface ModuleConfig {
  id: string;
  name: string;
  description: string;
  icon: string;
  enabled: boolean;
  category: string;
  settings: Record<string, unknown>;
}

const DEFAULT_MODULES: ModuleConfig[] = [
  {
    id: "memory",
    name: "Memory System",
    description:
      "Message monitoring, user profiling, personality analysis — /profile /remember /servermap",
    icon: "🧠",
    enabled: true,
    category: "Core",
    settings: {},
  },
  {
    id: "chat",
    name: "Jamie Chat",
    description: "Dedicated channel + @mentions + /talk /ask /join /leave",
    icon: "🔥",
    enabled: true,
    category: "Core",
    settings: {},
  },
  {
    id: "image_gen",
    name: "Image Generation",
    description: "/generate and /imagine image commands",
    icon: "🎨",
    enabled: true,
    category: "Core",
    settings: {},
  },
  {
    id: "moderation",
    name: "Moderation",
    description: "/mod ban kick mute warn lock softban + active cases",
    icon: "🛡️",
    enabled: true,
    category: "Safety",
    settings: {},
  },
  {
    id: "modlog",
    name: "Mod Logs",
    description: "/modlog cases, warnings, staff notes, modstats",
    icon: "📋",
    enabled: true,
    category: "Safety",
    settings: {},
  },
  {
    id: "manage",
    name: "Server Manage",
    description: "/manage roles purge announce modules prefix ignores",
    icon: "🛠️",
    enabled: true,
    category: "Safety",
    settings: {},
  },
];

const CATEGORIES = ["Core", "Safety"];

export default function ModulesPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState("");
  const [modules, setModules] = useState<ModuleConfig[]>(DEFAULT_MODULES);
  const [activeCategory, setActiveCategory] = useState("All");
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

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

  useEffect(() => {
    if (!selectedGuild) return;
    setStatusMsg("");
    (async () => {
      try {
        const res = await fetch(`/api/modules?guildId=${encodeURIComponent(selectedGuild)}`);
        const data = await res.json();
        if (data.modules) {
          setModules(data.modules);
        }
      } catch (e: unknown) {
        setStatusMsg(e instanceof Error ? e.message : String(e));
      }
    })();
  }, [selectedGuild]);

  function toggleModule(id: string) {
    setModules((prev) =>
      prev.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m))
    );
  }

  const filteredModules =
    activeCategory === "All"
      ? modules
      : modules.filter((m) => m.category === activeCategory);

  const enabledCount = modules.filter((m) => m.enabled).length;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
              Modules
            </h1>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Modules are always-on features (set once). Slash commands are for
              live actions. {enabledCount}/{modules.length} listed.
            </p>
          </div>
          <select
            value={selectedGuild}
            onChange={(e) => setSelectedGuild(e.target.value)}
            className="select"
            style={{ width: 220 }}
          >
            <option value="">Select server…</option>
            {guilds.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>

        {statusMsg && (
          <p
            className="text-sm mb-4"
            style={{
              color: statusMsg.toLowerCase().includes("fail")
                ? "var(--danger)"
                : "var(--accent)",
            }}
          >
            {statusMsg}
          </p>
        )}

        <div className="flex gap-2 mb-6 flex-wrap">
          {["All", ...CATEGORIES].map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveCategory(cat)}
              className="btn"
              style={{
                background:
                  activeCategory === cat ? "var(--primary-dim)" : "transparent",
                color:
                  activeCategory === cat ? "var(--primary)" : "var(--muted)",
                border:
                  activeCategory === cat
                    ? "1px solid rgba(57,183,196,0.3)"
                    : "1px solid var(--line)",
                fontSize: "0.8rem",
                padding: "6px 12px",
              }}
            >
              {cat}
            </button>
          ))}
        </div>

        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}
        >
          {filteredModules.map((mod) => (
            <div
              key={mod.id}
              className="card animate-fade"
              style={{ opacity: mod.enabled ? 1 : 0.65 }}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center justify-center rounded-lg text-lg"
                    style={{
                      width: 36,
                      height: 36,
                      background: mod.enabled
                        ? "var(--primary-dim)"
                        : "var(--surface3)",
                      border: mod.enabled
                        ? "1px solid rgba(57,183,196,0.3)"
                        : "1px solid var(--line)",
                    }}
                  >
                    {mod.icon}
                  </div>
                  <div>
                    <div
                      className="font-bold text-sm"
                      style={{
                        color: mod.enabled ? "var(--text)" : "var(--faint)",
                      }}
                    >
                      {mod.name}
                    </div>
                    <span className="badge badge-core">{mod.category}</span>
                  </div>
                </div>
                <div
                  className={`toggle ${mod.enabled ? "active" : ""}`}
                  onClick={() => toggleModule(mod.id)}
                  role="switch"
                  aria-checked={mod.enabled}
                />
              </div>

              <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
                {mod.description}
              </p>
            </div>
          ))}
        </div>
      </main>
      <JamieChat
        guildId={selectedGuild || undefined}
        guildContext={
          selectedGuild
            ? `Configuring modules for server ${guilds.find((g) => g.id === selectedGuild)?.name} (${selectedGuild}).`
            : ""
        }
      />
    </div>
  );
}
