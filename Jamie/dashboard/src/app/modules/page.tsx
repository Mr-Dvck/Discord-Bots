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
  settings: Record<string, any>;
}

const DEFAULT_MODULES: ModuleConfig[] = [
  {
    id: "moderation",
    name: "Moderation",
    description: "Auto-mod, warnings, bans, kicks, mutes, and mod logging",
    icon: "🛡️",
    enabled: true,
    category: "Safety",
    settings: { auto_delete_spam: true, warn_threshold: 3, log_channel: "" },
  },
  {
    id: "automod",
    name: "Automod",
    description: "Automatic message filtering, link blocking, word filter",
    icon: "🤖",
    enabled: true,
    category: "Safety",
    settings: { filter_links: false, filter_words: [], caps_threshold: 70 },
  },
  {
    id: "welcome",
    name: "Welcome",
    description: "Welcome messages, auto-role on join, DM greetings",
    icon: "👋",
    enabled: true,
    category: "Onboarding",
    settings: { welcome_channel: "", welcome_message: "", auto_role: "", dm_on_join: false },
  },
  {
    id: "autoroles",
    name: "Autoroles",
    description: "Joinable ranks, reaction roles, timed auto-roles",
    icon: "🎭",
    enabled: true,
    category: "Onboarding",
    settings: { joinable_ranks: [], reaction_roles_channel: "" },
  },
  {
    id: "levels",
    name: "Levels",
    description: "XP system, leveling, rank cards, leaderboards",
    icon: "📈",
    enabled: true,
    category: "Engagement",
    settings: { xp_per_message: 15, xp_cooldown: 60, level_up_channel: "" },
  },
  {
    id: "chat",
    name: "Jamie Chat",
    description: "Jamie responds in dedicated channel and when @mentioned",
    icon: "🔥",
    enabled: true,
    category: "Engagement",
    settings: { dedicated_channel: "", respond_to_mentions: true, personality: "default" },
  },
  {
    id: "image_gen",
    name: "Image Generation",
    description: "Generate images with /generate and /imagine commands",
    icon: "🎨",
    enabled: true,
    category: "Engagement",
    settings: { max_generations_per_day: 50, nsfw_filter: true },
  },
  {
    id: "memory",
    name: "Memory System",
    description: "Message monitoring, user profiling, personality analysis",
    icon: "🧠",
    enabled: true,
    category: "Core",
    settings: { max_messages_per_guild: 5000, analysis_interval: 30, min_messages_for_analysis: 15 },
  },
  {
    id: "reminders",
    name: "Reminders",
    description: "Set personal reminders, scheduled messages",
    icon: "⏰",
    enabled: false,
    category: "Utility",
    settings: { max_reminders_per_user: 10 },
  },
  {
    id: "giveaways",
    name: "Giveaways",
    description: "Host giveaways with reaction entry",
    icon: "🎁",
    enabled: false,
    category: "Engagement",
    settings: { default_duration: 86400 },
  },
  {
    id: "starboard",
    name: "Starboard",
    description: "Save best messages via star reactions",
    icon: "⭐",
    enabled: false,
    category: "Engagement",
    settings: { star_threshold: 3, starboard_channel: "" },
  },
  {
    id: "tickets",
    name: "Tickets",
    description: "Support ticket system with private channels",
    icon: "🎫",
    enabled: false,
    category: "Support",
    settings: { ticket_category: "", staff_role: "", log_channel: "" },
  },
  {
    id: "auto_message",
    name: "Auto Message",
    description: "Scheduled messages, timed announcements",
    icon: "📢",
    enabled: false,
    category: "Automation",
    settings: { messages: [] },
  },
  {
    id: "autoresponder",
    name: "Autoresponder",
    description: "Auto-reply to specific triggers and keywords",
    icon: "⚡",
    enabled: false,
    category: "Automation",
    settings: { triggers: [] },
  },
  {
    id: "action_log",
    name: "Action Log",
    description: "Log all moderation actions, joins, leaves, edits, deletes",
    icon: "📋",
    enabled: true,
    category: "Safety",
    settings: { log_channel: "", log_edits: true, log_deletes: true },
  },
];

const CATEGORIES = ["Core", "Safety", "Onboarding", "Engagement", "Utility", "Support", "Automation"];

export default function ModulesPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState("");
  const [modules, setModules] = useState<ModuleConfig[]>(DEFAULT_MODULES);
  const [activeCategory, setActiveCategory] = useState("All");
  const [editingModule, setEditingModule] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setGuilds(data);
      })
      .catch(() => {});
  }, []);

  function toggleModule(id: string) {
    setModules((prev) =>
      prev.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m))
    );
  }

  function updateSetting(moduleId: string, key: string, value: any) {
    setModules((prev) =>
      prev.map((m) =>
        m.id === moduleId
          ? { ...m, settings: { ...m.settings, [key]: value } }
          : m
      )
    );
  }

  async function saveConfig() {
    setSaving(true);
    // In a real implementation, this would save to the bot's database
    // For now, we simulate a save
    await new Promise((r) => setTimeout(r, 500));
    setSaving(false);
    alert("Configuration saved! Jamie will apply these settings.");
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
              ⚙️ Modules
            </h1>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              {enabledCount}/{modules.length} modules enabled
            </p>
          </div>
          <div className="flex gap-2">
            <select
              value={selectedGuild}
              onChange={(e) => setSelectedGuild(e.target.value)}
              className="select"
              style={{ width: 200 }}
            >
              <option value="">Select server...</option>
              {guilds.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
            <button
              onClick={saveConfig}
              disabled={saving}
              className="btn btn-accent"
            >
              {saving ? "Saving..." : "💾 Save Config"}
            </button>
          </div>
        </div>

        {/* Category filter */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {["All", ...CATEGORIES].map((cat) => (
            <button
              key={cat}
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

        {/* Module cards */}
        <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))" }}>
          {filteredModules.map((mod) => (
            <div
              key={mod.id}
              className="card animate-fade"
              style={{
                opacity: mod.enabled ? 1 : 0.6,
              }}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div
                    className="flex items-center justify-center rounded-lg text-lg"
                    style={{
                      width: 36,
                      height: 36,
                      background: mod.enabled ? "var(--primary-dim)" : "var(--surface3)",
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
                      style={{ color: mod.enabled ? "var(--text)" : "var(--faint)" }}
                    >
                      {mod.name}
                    </div>
                    <span className="badge badge-core">{mod.category}</span>
                  </div>
                </div>

                {/* Toggle */}
                <div
                  className={`toggle ${mod.enabled ? "active" : ""}`}
                  onClick={() => toggleModule(mod.id)}
                />
              </div>

              <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
                {mod.description}
              </p>

              {/* Settings (collapsible) */}
              {mod.enabled && Object.keys(mod.settings).length > 0 && (
                <div>
                  <button
                    onClick={() =>
                      setEditingModule(
                      editingModule === mod.id ? null : mod.id
                    )
                  }
                    className="btn btn-ghost"
                    style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                  >
                    {editingModule === mod.id ? "▾ Settings" : "▸ Settings"}
                  </button>

                  {editingModule === mod.id && (
                    <div
                      className="mt-3 p-3 rounded-lg space-y-2 animate-fade"
                      style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                      }}
                    >
                      {Object.entries(mod.settings).map(([key, value]) => (
                        <div
                          key={key}
                          className="flex items-center gap-2"
                        >
                          <label
                            className="text-xs font-medium shrink-0"
                            style={{
                              color: "var(--muted)",
                              width: 130,
                              textTransform: "uppercase",
                              letterSpacing: "0.05em",
                            }}
                          >
                            {key.replace(/_/g, " ")}
                          </label>
                          {typeof value === "boolean" ? (
                            <div
                              className={`toggle ${value ? "active" : ""}`}
                              onClick={() => updateSetting(mod.id, key, !value)}
                              style={{ transform: "scale(0.8)" }}
                            />
                          ) : typeof value === "number" ? (
                            <input
                              type="number"
                              value={value}
                              onChange={(e) =>
                                updateSetting(mod.id, key, Number(e.target.value))
                              }
                              className="input"
                              style={{ width: 100, padding: "6px 10px", fontSize: "0.8rem" }}
                            />
                          ) : Array.isArray(value) ? (
                            <span
                              className="text-xs"
                              style={{ color: "var(--faint)" }}
                            >
                              [{value.length} items]
                            </span>
                          ) : (
                            <input
                              type="text"
                              value={String(value)}
                              onChange={(e) =>
                                updateSetting(mod.id, key, e.target.value)
                              }
                              className="input flex-1"
                              style={{ padding: "6px 10px", fontSize: "0.8rem" }}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </main>
      <JamieChat
        guildContext={selectedGuild ? `Configuring modules for server ${guilds.find(g => g.id === selectedGuild)?.name}` : ""}
      />
    </div>
  );
}
