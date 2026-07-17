"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
}

interface BlueprintCategory {
  name: string;
  channels: {
    name: string;
    type: string;
    topic?: string;
    nsfw?: boolean;
  }[];
}

interface BlueprintRole {
  name: string;
  color?: string;
  hoist?: boolean;
}

interface Blueprint {
  categories: BlueprintCategory[];
  roles: BlueprintRole[];
}

interface BuildResult {
  roles: any[];
  channels: any[];
  errors: string[];
}

const PRESET_TEMPLATES: Record<string, string> = {
  gaming: "A gaming community server with areas for different games, voice channels, LFG, announcements, and staff sections",
  music: "A music community server with genre channels, listening parties, sharing, production, and DJ areas",
  metal: "A metal music community with subgenre channels, recommendations, discussion, merch, and show planning",
  general: "A general community server with welcome, chat, memes, media, voice, and staff areas",
  creator: "A content creator server with announcements, fan areas, collaboration, feedback, and behind-the-scenes",
  crypto: "A crypto/DeFi server with trading channels, project discussions, alpha, education, and alerts",
};

export default function BuilderPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState("");
  const [description, setDescription] = useState("");
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [rawBlueprint, setRawBlueprint] = useState("");
  const [generating, setGenerating] = useState(false);
  const [building, setBuilding] = useState(false);
  const [results, setResults] = useState<BuildResult | null>(null);
  const [activeTab, setActiveTab] = useState<"ai" | "manual">("ai");

  // Manual builder state
  const [manualBlueprint, setManualBlueprint] = useState<Blueprint>({
    categories: [
      { name: "Information", channels: [{ name: "welcome", type: "text", topic: "Server info and rules" }, { name: "announcements", type: "text", topic: "Important updates" }] },
      { name: "General", channels: [{ name: "chat", type: "text", topic: "General discussion" }, { name: "memes", type: "text" }, { name: "voice-chat", type: "voice" }] },
    ],
    roles: [{ name: "Admin", color: "#f04747", hoist: true }, { name: "Moderator", color: "#39b7c4", hoist: true }, { name: "Member", color: "#7dd3a7" }],
  });

  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setGuilds(data);
      })
      .catch(() => {});
  }, []);

  async function generateBlueprint() {
    if (!description.trim()) return;
    setGenerating(true);
    setBlueprint(null);
    setResults(null);
    try {
      const res = await fetch("/api/generate-blueprint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setRawBlueprint(data.raw || "");
      if (data.blueprint) {
        setBlueprint(data.blueprint);
      }
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setGenerating(false);
    }
  }

  async function buildServer(bp: Blueprint) {
    if (!selectedGuild) {
      alert("Select a server first");
      return;
    }
    setBuilding(true);
    setResults(null);
    try {
      const res = await fetch(`/api/guilds/${selectedGuild}/build`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bp),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setResults(data);
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setBuilding(false);
    }
  }

  // Manual blueprint editing helpers
  function addCategory() {
    setManualBlueprint((prev) => ({
      ...prev,
      categories: [...prev.categories, { name: "New Category", channels: [] }],
    }));
  }

  function removeCategory(idx: number) {
    setManualBlueprint((prev) => ({
      ...prev,
      categories: prev.categories.filter((_, i) => i !== idx),
    }));
  }

  function addChannel(catIdx: number) {
    setManualBlueprint((prev) => {
      const cats = [...prev.categories];
      cats[catIdx] = {
        ...cats[catIdx],
        channels: [...cats[catIdx].channels, { name: "new-channel", type: "text" }],
      };
      return { ...prev, categories: cats };
    });
  }

  function removeChannel(catIdx: number, chIdx: number) {
    setManualBlueprint((prev) => {
      const cats = [...prev.categories];
      cats[catIdx] = {
        ...cats[catIdx],
        channels: cats[catIdx].channels.filter((_, i) => i !== chIdx),
      };
      return { ...prev, categories: cats };
    });
  }

  function updateCategoryName(catIdx: number, name: string) {
    setManualBlueprint((prev) => {
      const cats = [...prev.categories];
      cats[catIdx] = { ...cats[catIdx], name };
      return { ...prev, categories: cats };
    });
  }

  function updateChannel(catIdx: number, chIdx: number, field: string, value: any) {
    setManualBlueprint((prev) => {
      const cats = [...prev.categories];
      const channels = [...cats[catIdx].channels];
      channels[chIdx] = { ...channels[chIdx], [field]: value };
      cats[catIdx] = { ...cats[catIdx], channels };
      return { ...prev, categories: cats };
    });
  }

  function addRole() {
    setManualBlueprint((prev) => ({
      ...prev,
      roles: [...prev.roles, { name: "New Role", color: "#39b7c4" }],
    }));
  }

  function removeRole(idx: number) {
    setManualBlueprint((prev) => ({
      ...prev,
      roles: prev.roles.filter((_, i) => i !== idx),
    }));
  }

  function updateRole(idx: number, field: string, value: any) {
    setManualBlueprint((prev) => {
      const roles = [...prev.roles];
      roles[idx] = { ...roles[idx], [field]: value };
      return { ...prev, roles };
    });
  }

  const activeBlueprint = activeTab === "ai" ? blueprint : manualBlueprint;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        <h1 className="text-xl font-bold mb-2" style={{ color: "var(--text)" }}>
          🏗️ Server Builder
        </h1>
        <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
          Build or revamp entire servers from scratch. Use AI to generate a blueprint or build manually.
        </p>

        {/* Guild selector */}
        <div className="card-sm mb-6">
          <h3 className="text-sm font-bold mb-2" style={{ color: "var(--text)" }}>
            Target Server
          </h3>
          <select
            value={selectedGuild}
            onChange={(e) => setSelectedGuild(e.target.value)}
            className="select"
          >
            <option value="">Select a server...</option>
            {guilds.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab("ai")}
            className="btn"
            style={{
              background: activeTab === "ai" ? "var(--premium-dim)" : "transparent",
              color: activeTab === "ai" ? "var(--premium)" : "var(--muted)",
              border: activeTab === "ai" ? "1px solid rgba(217,138,255,0.3)" : "1px solid var(--line)",
            }}
          >
            🤖 AI Generate
          </button>
          <button
            onClick={() => setActiveTab("manual")}
            className="btn"
            style={{
              background: activeTab === "manual" ? "var(--primary-dim)" : "transparent",
              color: activeTab === "manual" ? "var(--primary)" : "var(--muted)",
              border: activeTab === "manual" ? "1px solid rgba(57,183,196,0.3)" : "1px solid var(--line)",
            }}
          >
            ✏️ Manual Builder
          </button>
        </div>

        {/* AI Generate tab */}
        {activeTab === "ai" && (
          <div className="space-y-4 animate-fade">
            <div className="card-sm">
              <h3 className="text-sm font-bold mb-3" style={{ color: "var(--text)" }}>
                Describe Your Server
              </h3>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what kind of server you want... e.g. 'A gaming community for FPS players with ranked channels, LFG, and tournament areas'"
                className="input"
                style={{ minHeight: 100, resize: "vertical" }}
              />

              {/* Preset templates */}
              <div className="flex gap-2 mt-3 flex-wrap">
                {Object.entries(PRESET_TEMPLATES).map(([key, desc]) => (
                  <button
                    key={key}
                    onClick={() => setDescription(desc)}
                    className="btn btn-ghost"
                    style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                  >
                    {key.charAt(0).toUpperCase() + key.slice(1)}
                  </button>
                ))}
              </div>

              <button
                onClick={generateBlueprint}
                disabled={generating || !description.trim()}
                className="btn btn-accent mt-3"
              >
                {generating ? "🤖 Generating..." : "🤖 Generate Blueprint"}
              </button>
            </div>

            {/* Generated blueprint preview */}
            {activeBlueprint && (
              <div className="card animate-fade">
                <h3 className="text-sm font-bold mb-3" style={{ color: "var(--premium)" }}>
                  📋 Generated Blueprint
                </h3>
                <BlueprintPreview blueprint={activeBlueprint} />

                <button
                  onClick={() => buildServer(activeBlueprint)}
                  disabled={building || !selectedGuild}
                  className="btn btn-primary mt-4"
                >
                  {building ? "🏗️ Building..." : "🏗️ Build Server"}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Manual Builder tab */}
        {activeTab === "manual" && (
          <div className="space-y-4 animate-fade">
            {/* Categories */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold" style={{ color: "var(--text)" }}>
                  📁 Categories & Channels
                </h3>
                <button onClick={addCategory} className="btn btn-ghost" style={{ fontSize: "0.75rem" }}>
                  + Category
                </button>
              </div>

              {manualBlueprint.categories.map((cat, catIdx) => (
                <div
                  key={catIdx}
                  className="mb-4 p-4 rounded-lg"
                  style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <input
                      type="text"
                      value={cat.name}
                      onChange={(e) => updateCategoryName(catIdx, e.target.value)}
                      className="input"
                      style={{ width: 200, fontWeight: 600 }}
                    />
                    <button
                      onClick={() => removeCategory(catIdx)}
                      className="btn btn-danger"
                      style={{ padding: "4px 8px", fontSize: "0.7rem" }}
                    >
                      ✕
                    </button>
                    <button
                      onClick={() => addChannel(catIdx)}
                      className="btn btn-ghost"
                      style={{ fontSize: "0.75rem", marginLeft: "auto" }}
                    >
                      + Channel
                    </button>
                  </div>

                  <div className="space-y-2 ml-2">
                    {cat.channels.map((ch, chIdx) => (
                      <div key={chIdx} className="flex items-center gap-2">
                        <select
                          value={ch.type}
                          onChange={(e) => updateChannel(catIdx, chIdx, "type", e.target.value)}
                          className="select"
                          style={{ width: 90 }}
                        >
                          <option value="text">💬 Text</option>
                          <option value="voice">🔊 Voice</option>
                          <option value="forum">📋 Forum</option>
                          <option value="stage">🎤 Stage</option>
                        </select>
                        <input
                          type="text"
                          value={ch.name}
                          onChange={(e) => updateChannel(catIdx, chIdx, "name", e.target.value)}
                          className="input flex-1"
                          placeholder="channel-name"
                        />
                        <input
                          type="text"
                          value={ch.topic || ""}
                          onChange={(e) => updateChannel(catIdx, chIdx, "topic", e.target.value)}
                          className="input flex-1"
                          placeholder="Topic (optional)"
                        />
                        <button
                          onClick={() => removeChannel(catIdx, chIdx)}
                          className="btn btn-danger"
                          style={{ padding: "4px 8px", fontSize: "0.7rem" }}
                        >
                          ✕
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Roles */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold" style={{ color: "var(--text)" }}>
                  🛡️ Roles
                </h3>
                <button onClick={addRole} className="btn btn-ghost" style={{ fontSize: "0.75rem" }}>
                  + Role
                </button>
              </div>

              <div className="space-y-2">
                {manualBlueprint.roles.map((role, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={role.name}
                      onChange={(e) => updateRole(idx, "name", e.target.value)}
                      className="input flex-1"
                      placeholder="Role name"
                    />
                    <input
                      type="color"
                      value={role.color || "#39b7c4"}
                      onChange={(e) => updateRole(idx, "color", e.target.value)}
                      className="w-8 h-8 rounded cursor-pointer"
                      style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
                    />
                    <label className="flex items-center gap-1 text-xs" style={{ color: "var(--muted)" }}>
                      <input
                        type="checkbox"
                        checked={role.hoist || false}
                        onChange={(e) => updateRole(idx, "hoist", e.target.checked)}
                      />
                      Hoist
                    </label>
                    <button
                      onClick={() => removeRole(idx)}
                      className="btn btn-danger"
                      style={{ padding: "4px 8px", fontSize: "0.7rem" }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Build button */}
            <div className="card-sm">
              <button
                onClick={() => buildServer(manualBlueprint)}
                disabled={building || !selectedGuild}
                className="btn btn-primary"
              >
                {building ? "🏗️ Building..." : "🏗️ Build Server"}
              </button>
            </div>
          </div>
        )}

        {/* Build results */}
        {results && (
          <div className="card mt-6 animate-fade">
            <h3 className="text-sm font-bold mb-3" style={{ color: "var(--accent)" }}>
              ✅ Build Results
            </h3>
            <div className="space-y-2">
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Created {results.channels.length} channels and {results.roles.length} roles
              </p>
              {results.errors.length > 0 && (
                <div>
                  <p className="text-sm font-bold" style={{ color: "var(--danger)" }}>
                    Errors ({results.errors.length}):
                  </p>
                  <ul className="text-xs space-y-1" style={{ color: "var(--faint)" }}>
                    {results.errors.map((e, i) => (
                      <li key={i}>• {e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
      <JamieChat guildContext={selectedGuild ? `Building server: ${guilds.find(g => g.id === selectedGuild)?.name}` : ""} />
    </div>
  );
}

function BlueprintPreview({ blueprint }: { blueprint: Blueprint }) {
  return (
    <div className="space-y-3">
      {blueprint.roles.length > 0 && (
        <div>
          <h4 className="text-xs font-bold uppercase mb-2" style={{ color: "var(--faint)" }}>
            Roles
          </h4>
          <div className="flex gap-2 flex-wrap">
            {blueprint.roles.map((role, i) => (
              <span
                key={i}
                className="badge"
                style={{
                  background: role.color ? `${role.color}20` : "var(--surface3)",
                  color: role.color || "var(--muted)",
                }}
              >
                {role.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {blueprint.categories.map((cat, i) => (
        <div key={i}>
          <h4 className="text-xs font-bold uppercase mb-2" style={{ color: "var(--faint)" }}>
            📁 {cat.name}
          </h4>
          <div className="flex gap-2 flex-wrap ml-2">
            {cat.channels.map((ch, j) => {
              const icon = ch.type === "voice" ? "🔊" : ch.type === "forum" ? "📋" : ch.type === "stage" ? "🎤" : "💬";
              return (
                <span key={j} className="badge badge-core">
                  {icon} #{ch.name}
                </span>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
