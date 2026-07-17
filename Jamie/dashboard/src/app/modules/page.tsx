"use client";

import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
}

interface Channel {
  id: string;
  name: string;
  type: number;
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

interface WelcomeSettings {
  channel_id: string;
  message: string;
  image_line: string;
  dm_on_join: boolean;
  background_path: string;
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
    description: "Dedicated channel + @mentions + /talk /ask",
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
    description: "/manage roles purge announce modules prefix ignores giveaway",
    icon: "🛠️",
    enabled: true,
    category: "Safety",
    settings: {},
  },
  {
    id: "ranks",
    name: "Ranks & Roles",
    description: "/ranks addrank rank list roles roleinfo — joinable ranks",
    icon: "🎭",
    enabled: true,
    category: "Onboarding",
    settings: {},
  },
  {
    id: "welcome",
    name: "Welcome",
    description:
      "Auto join welcome code blocks. No slash setup — turn on here, set channel + text.",
    icon: "👋",
    enabled: false,
    category: "Onboarding",
    settings: {},
  },
  {
    id: "starboard",
    name: "Starboard",
    description:
      "Auto join starboard. Reposts highly starred messages (⭐) to a dedicated channel.",
    icon: "⭐",
    enabled: false,
    category: "Engagement",
    settings: {},
  },
  {
    id: "economy",
    name: "Economy",
    description: "/economy daily work pay — coin rewards",
    icon: "💰",
    enabled: true,
    category: "Engagement",
    settings: {},
  },
  {
    id: "giveaways",
    name: "Giveaways",
    description: "/manage giveaway — reaction entry giveaways",
    icon: "🎁",
    enabled: true,
    category: "Engagement",
    settings: {},
  },
  {
    id: "misc",
    name: "Misc Utilities",
    description: "/misc afk whois remindme serverinfo roll highlights…",
    icon: "✨",
    enabled: true,
    category: "Utility",
    settings: {},
  },
  {
    id: "bot_info",
    name: "Bot Info",
    description: "/bot info stats uptime ping premium",
    icon: "📡",
    enabled: true,
    category: "Utility",
    settings: {},
  },
];

const CATEGORIES = ["Core", "Safety", "Onboarding", "Engagement", "Utility"];

const DEFAULT_WELCOME: WelcomeSettings = {
  channel_id: "",
  message: "Welcome {user} — you are now Certified.",
  image_line: "is now Certified",
  dm_on_join: false,
  background_path: "",
};

interface StarboardSettings {
  channel_id: string;
  min_stars: number;
}

const DEFAULT_STARBOARD: StarboardSettings = {
  channel_id: "",
  min_stars: 3,
};

export default function ModulesPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState("");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [modules, setModules] = useState<ModuleConfig[]>(DEFAULT_MODULES);
  const [welcome, setWelcome] = useState<WelcomeSettings>(DEFAULT_WELCOME);
  const [starboard, setStarboard] = useState<StarboardSettings>(DEFAULT_STARBOARD);
  const [activeCategory, setActiveCategory] = useState("All");
  const [editingModule, setEditingModule] = useState<string | null>("welcome");
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [genBg, setGenBg] = useState(false);
  const [bgPreview, setBgPreview] = useState("");

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

  const loadWelcome = useCallback(async (guildId: string) => {
    if (!guildId) return;
    setStatusMsg("");
    try {
      const [wRes, gRes, sRes] = await Promise.all([
        fetch(`/api/welcome?guildId=${encodeURIComponent(guildId)}`),
        fetch(`/api/guilds/${guildId}`),
        fetch(`/api/starboard?guildId=${encodeURIComponent(guildId)}`),
      ]);
      const wData = await wRes.json();
      const gData = await gRes.json();
      const sData = await sRes.json();

      if (Array.isArray(gData.channels)) {
        setChannels(
          gData.channels.filter((c: Channel) => c.type === 0 || c.type === 5)
        );
      } else {
        setChannels([]);
      }

      if (wData.config) {
        const c = wData.config;
        setWelcome({
          channel_id: c.channel_id || "",
          message: c.message || DEFAULT_WELCOME.message,
          image_line: c.image_line || DEFAULT_WELCOME.image_line,
          dm_on_join: Boolean(c.dm_on_join),
          background_path: c.background_path || "",
        });
        setModules((prev) =>
          prev.map((m) =>
            m.id === "welcome" ? { ...m, enabled: Boolean(c.enabled) } : m
          )
        );
      }

      if (sData.config) {
        const c = sData.config;
        setStarboard({
          channel_id: c.channel_id || "",
          min_stars: Number(c.min_stars) || 3,
        });
        setModules((prev) =>
          prev.map((m) =>
            m.id === "starboard" ? { ...m, enabled: Boolean(c.enabled) } : m
          )
        );
      }
    } catch (e: unknown) {
      setStatusMsg(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    if (selectedGuild) loadWelcome(selectedGuild);
  }, [selectedGuild, loadWelcome]);

  function toggleModule(id: string) {
    setModules((prev) =>
      prev.map((m) => (m.id === id ? { ...m, enabled: !m.enabled } : m))
    );
  }

  async function saveStarboard() {
    if (!selectedGuild) {
      setStatusMsg("Select a server first.");
      return;
    }
    const starboardMod = modules.find((m) => m.id === "starboard");
    if (starboardMod?.enabled && !starboard.channel_id) {
      setStatusMsg("Pick a starboard channel before enabling.");
      return;
    }

    setSaving(true);
    setStatusMsg("");
    try {
      const res = await fetch("/api/starboard", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guildId: selectedGuild,
          enabled: Boolean(starboardMod?.enabled),
          channel_id: starboard.channel_id || null,
          min_stars: Number(starboard.min_stars) || 3,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Save failed");
      setStatusMsg(
        starboardMod?.enabled
          ? "Starboard module saved. Starred posts will be logged."
          : "Starboard module saved (disabled)."
      );
    } catch (e: unknown) {
      setStatusMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function saveWelcome() {
    if (!selectedGuild) {
      setStatusMsg("Select a server first.");
      return;
    }
    const welcomeMod = modules.find((m) => m.id === "welcome");
    if (welcomeMod?.enabled && !welcome.channel_id) {
      setStatusMsg("Pick a welcome channel before enabling.");
      return;
    }

    setSaving(true);
    setStatusMsg("");
    try {
      const res = await fetch("/api/welcome", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guildId: selectedGuild,
          enabled: Boolean(welcomeMod?.enabled),
          channel_id: welcome.channel_id || null,
          message: welcome.message,
          image_line: welcome.image_line,
          dm_on_join: welcome.dm_on_join,
          background_path: welcome.background_path,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Save failed");
      setStatusMsg(
        welcomeMod?.enabled
          ? "Welcome module saved. Joins will auto-post banners."
          : "Welcome module saved (disabled)."
      );
    } catch (e: unknown) {
      setStatusMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function generateBackground() {
    if (!selectedGuild) {
      setStatusMsg("Select a server first.");
      return;
    }
    setGenBg(true);
    setStatusMsg("Generating welcome background…");
    try {
      const res = await fetch("/api/welcome/background", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guildId: selectedGuild }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Background failed");
      setWelcome((w) => ({
        ...w,
        background_path: data.path || w.background_path,
      }));
      if (data.dataUrl) setBgPreview(data.dataUrl);
      setStatusMsg("Background saved. Joins reuse this art (no AI per join).");
    } catch (e: unknown) {
      setStatusMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setGenBg(false);
    }
  }

  const filteredModules =
    activeCategory === "All"
      ? modules
      : modules.filter((m) => m.category === activeCategory);

  const enabledCount = modules.filter((m) => m.enabled).length;
  const welcomeEnabled = modules.find((m) => m.id === "welcome")?.enabled;

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

              {mod.id === "welcome" && (
                <div>
                  <button
                    type="button"
                    onClick={() =>
                      setEditingModule(
                        editingModule === "welcome" ? null : "welcome"
                      )
                    }
                    className="btn btn-ghost"
                    style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                  >
                    {editingModule === "welcome" ? "▾ Settings" : "▸ Settings"}
                  </button>

                  {editingModule === "welcome" && (
                    <div
                      className="mt-3 p-3 rounded-lg space-y-3 animate-fade"
                      style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                      }}
                    >
                      {!selectedGuild && (
                        <p className="text-xs" style={{ color: "var(--danger)" }}>
                          Select a server above to load/save welcome settings.
                        </p>
                      )}

                      <label className="block text-xs" style={{ color: "var(--faint)" }}>
                        Welcome channel
                        <select
                          className="select mt-1 w-full"
                          value={welcome.channel_id}
                          onChange={(e) =>
                            setWelcome((w) => ({
                              ...w,
                              channel_id: e.target.value,
                            }))
                          }
                          disabled={!selectedGuild}
                        >
                          <option value="">Select channel…</option>
                          {channels.map((c) => (
                            <option key={c.id} value={c.id}>
                              #{c.name}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="block text-xs" style={{ color: "var(--faint)" }}>
                        Chat message ({`{user}`} {`{server}`} {`{membercount}`})
                        <input
                          className="input mt-1 w-full"
                          value={welcome.message}
                          onChange={(e) =>
                            setWelcome((w) => ({ ...w, message: e.target.value }))
                          }
                        />
                      </label>

                      <label
                        className="flex items-center gap-2 text-xs cursor-pointer"
                        style={{ color: "var(--muted)" }}
                      >
                        <input
                          type="checkbox"
                          checked={welcome.dm_on_join}
                          onChange={(e) =>
                            setWelcome((w) => ({
                              ...w,
                              dm_on_join: e.target.checked,
                            }))
                          }
                        />
                        Also DM the welcome message on join
                      </label>

                      <button
                        type="button"
                        className="btn btn-accent w-full"
                        disabled={saving || !selectedGuild}
                        onClick={saveWelcome}
                        style={{ justifyContent: "center" }}
                      >
                        {saving
                          ? "Saving…"
                          : welcomeEnabled
                            ? "Save & enable Welcome"
                            : "Save Welcome settings"}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {mod.id === "starboard" && (
                <div>
                  <button
                    type="button"
                    onClick={() =>
                      setEditingModule(
                        editingModule === "starboard" ? null : "starboard"
                      )
                    }
                    className="btn btn-ghost"
                    style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                  >
                    {editingModule === "starboard" ? "▾ Settings" : "▸ Settings"}
                  </button>

                  {editingModule === "starboard" && (
                    <div
                      className="mt-3 p-3 rounded-lg space-y-3 animate-fade"
                      style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                      }}
                    >
                      {!selectedGuild && (
                        <p className="text-xs" style={{ color: "var(--danger)" }}>
                          Select a server above to load/save starboard settings.
                        </p>
                      )}

                      <label className="block text-xs" style={{ color: "var(--faint)" }}>
                        Starboard channel
                        <select
                          className="select mt-1 w-full"
                          value={starboard.channel_id}
                          onChange={(e) =>
                            setStarboard((w) => ({
                              ...w,
                              channel_id: e.target.value,
                            }))
                          }
                          disabled={!selectedGuild}
                        >
                          <option value="">Select channel…</option>
                          {channels.map((c) => (
                            <option key={c.id} value={c.id}>
                              #{c.name}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="block text-xs" style={{ color: "var(--faint)" }}>
                        Minimum stars required
                        <input
                          type="number"
                          min="1"
                          max="20"
                          className="input mt-1 w-full"
                          value={starboard.min_stars}
                          onChange={(e) =>
                            setStarboard((w) => ({ ...w, min_stars: Number(e.target.value) || 3 }))
                          }
                          disabled={!selectedGuild}
                        />
                      </label>

                      <button
                        type="button"
                        className="btn btn-accent w-full"
                        disabled={saving || !selectedGuild}
                        onClick={saveStarboard}
                        style={{ justifyContent: "center" }}
                      >
                        {saving
                          ? "Saving…"
                          : modules.find((m) => m.id === "starboard")?.enabled
                            ? "Save & enable Starboard"
                            : "Save Starboard settings"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </main>
      <JamieChat
        guildId={selectedGuild || undefined}
        guildContext={
          selectedGuild
            ? `Configuring modules for server ${guilds.find((g) => g.id === selectedGuild)?.name} (${selectedGuild}). Welcome is a module (auto on join), not slash commands.`
            : ""
        }
      />
    </div>
  );
}
