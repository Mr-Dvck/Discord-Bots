"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Channel {
  id: string;
  name: string;
  type: number;
  parent_id: string | null;
  topic: string | null;
  position: number;
  nsfw: boolean;
}

interface Role {
  id: string;
  name: string;
  color: number;
  hoist: boolean;
  permissions: string;
  position: number;
}

interface Member {
  user: { id: string; username: string; display_name?: string; avatar?: string };
  roles: string[];
  joined_at: string;
}

interface GuildData {
  guild: { id: string; name: string; icon: string | null; member_count?: number };
  channels: Channel[];
  roles: Role[];
  members: Member[];
}

const TYPE_LABELS: Record<number, string> = {
  0: "💬 Text",
  2: "🔊 Voice",
  4: "📁 Category",
  13: "🎤 Stage",
  15: "📋 Forum",
};

export default function ServerDetailPage() {
  const params = useParams();
  const guildId = params.id as string;
  const [data, setData] = useState<GuildData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"channels" | "roles" | "members">("channels");

  // Channel creation
  const [newChannelName, setNewChannelName] = useState("");
  const [newChannelType, setNewChannelType] = useState(0);
  const [newChannelParent, setNewChannelParent] = useState("");
  const [newChannelTopic, setNewChannelTopic] = useState("");
  const [creating, setCreating] = useState(false);

  // Role creation
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleColor, setNewRoleColor] = useState("#39b7c4");
  const [creatingRole, setCreatingRole] = useState(false);

  useEffect(() => {
    fetch(`/api/guilds/${guildId}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) throw new Error(d.error);
        setData(d);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [guildId]);

  async function createChannel() {
    if (!newChannelName.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`/api/guilds/${guildId}/channels`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newChannelName.trim(),
          type: newChannelType,
          parent_id: newChannelParent || undefined,
          topic: newChannelTopic || undefined,
        }),
      });
      const ch = await res.json();
      if (ch.error) throw new Error(ch.error);
      setData((prev) => prev ? { ...prev, channels: [...prev.channels, ch] } : prev);
      setNewChannelName("");
      setNewChannelTopic("");
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setCreating(false);
    }
  }

  async function deleteChannel(channelId: string) {
    if (!confirm("Delete this channel?")) return;
    try {
      await fetch(`/api/guilds/${guildId}/channels`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channelId }),
      });
      setData((prev) =>
        prev ? { ...prev, channels: prev.channels.filter((c) => c.id !== channelId) } : prev
      );
    } catch (e: any) {
      alert("Error: " + e.message);
    }
  }

  async function createRole() {
    if (!newRoleName.trim()) return;
    setCreatingRole(true);
    try {
      const res = await fetch(`/api/guilds/${guildId}/roles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newRoleName.trim(),
          color: parseInt(newRoleColor.replace("#", ""), 16),
          hoist: false,
        }),
      });
      const role = await res.json();
      if (role.error) throw new Error(role.error);
      setData((prev) => prev ? { ...prev, roles: [...prev.roles, role] } : prev);
      setNewRoleName("");
    } catch (e: any) {
      alert("Error: " + e.message);
    } finally {
      setCreatingRole(false);
    }
  }

  async function deleteRole(roleId: string) {
    if (!confirm("Delete this role?")) return;
    try {
      await fetch(`/api/guilds/${guildId}/roles`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roleId }),
      });
      setData((prev) =>
        prev ? { ...prev, roles: prev.roles.filter((r) => r.id !== roleId) } : prev
      );
    } catch (e: any) {
      alert("Error: " + e.message);
    }
  }

  if (loading) return <div className="flex min-h-screen"><Sidebar /><main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}><p style={{ color: "var(--faint)" }}>Loading server...</p></main></div>;
  if (error || !data) return <div className="flex min-h-screen"><Sidebar /><main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}><p style={{ color: "var(--danger)" }}>Error: {error}</p></main></div>;

  const categories = data.channels.filter((c) => c.type === 4);
  const nonCategoryChannels = data.channels.filter((c) => c.type !== 4);

  // Group channels by parent
  const channelsByParent: Record<string, Channel[]> = {};
  for (const ch of nonCategoryChannels) {
    const parentId = ch.parent_id || "__none__";
    if (!channelsByParent[parentId]) channelsByParent[parentId] = [];
    channelsByParent[parentId].push(ch);
  }

  const guildContext = `Current server: ${data.guild.name} (${data.guild.id}), ${data.channels.length} channels, ${data.roles.length} roles, ${data.members.length} members visible`;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        {/* Server header */}
        <div className="card mb-6 animate-fade">
          <div className="flex items-center gap-4">
            {data.guild.icon ? (
              <img
                src={`https://cdn.discordapp.com/icons/${data.guild.id}/${data.guild.icon}.png?size=128`}
                alt={data.guild.name}
                className="w-14 h-14 rounded-full"
              />
            ) : (
              <div
                className="flex items-center justify-center rounded-full text-xl font-bold"
                style={{
                  width: 56,
                  height: 56,
                  background: "var(--primary-dim)",
                  color: "var(--primary)",
                }}
              >
                {data.guild.name.charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
                {data.guild.name}
              </h1>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                {data.guild.member_count || data.members.length} members • {data.channels.length} channels • {data.roles.length} roles
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          {(["channels", "roles", "members"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="btn"
              style={{
                background: activeTab === tab ? "var(--primary-dim)" : "transparent",
                color: activeTab === tab ? "var(--primary)" : "var(--muted)",
                border: activeTab === tab ? "1px solid rgba(57,183,196,0.3)" : "1px solid var(--line)",
              }}
            >
              {tab === "channels" ? "💬" : tab === "roles" ? "🛡️" : "👥"}{" "}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Channels tab */}
        {activeTab === "channels" && (
          <div className="space-y-4 animate-fade">
            {/* Create channel */}
            <div className="card-sm">
              <h3 className="text-sm font-bold mb-3" style={{ color: "var(--text)" }}>
                + Create Channel
              </h3>
              <div className="flex gap-2 flex-wrap">
                <input
                  type="text"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  placeholder="channel-name"
                  className="input flex-1"
                  style={{ minWidth: 180 }}
                />
                <select
                  value={newChannelType}
                  onChange={(e) => setNewChannelType(Number(e.target.value))}
                  className="select"
                  style={{ width: 130 }}
                >
                  <option value={0}>💬 Text</option>
                  <option value={2}>🔊 Voice</option>
                  <option value={15}>📋 Forum</option>
                  <option value={13}>🎤 Stage</option>
                </select>
                <select
                  value={newChannelParent}
                  onChange={(e) => setNewChannelParent(e.target.value)}
                  className="select"
                  style={{ width: 160 }}
                >
                  <option value="">No Category</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  value={newChannelTopic}
                  onChange={(e) => setNewChannelTopic(e.target.value)}
                  placeholder="Topic (optional)"
                  className="input flex-1"
                  style={{ minWidth: 150 }}
                />
                <button
                  onClick={createChannel}
                  disabled={creating || !newChannelName.trim()}
                  className="btn btn-primary"
                >
                  {creating ? "..." : "Create"}
                </button>
              </div>
            </div>

            {/* Channel tree */}
            {categories.map((cat) => (
              <div key={cat.id} className="card-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm">📁</span>
                  <span className="font-bold text-sm" style={{ color: "var(--text)" }}>
                    {cat.name}
                  </span>
                  <span className="badge badge-core">
                    {channelsByParent[cat.id]?.length || 0} channels
                  </span>
                </div>
                <div className="space-y-1 ml-4">
                  {(channelsByParent[cat.id] || []).map((ch) => (
                    <div
                      key={ch.id}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg"
                      style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
                    >
                      <span className="text-sm">{TYPE_LABELS[ch.type] || "📌"}</span>
                      <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
                        #{ch.name}
                      </span>
                      {ch.topic && (
                        <span className="text-xs flex-1 truncate" style={{ color: "var(--faint)" }}>
                          — {ch.topic}
                        </span>
                      )}
                      {ch.nsfw && <span className="badge badge-danger">NSFW</span>}
                      <button
                        onClick={() => deleteChannel(ch.id)}
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

            {/* Uncategorised channels */}
            {channelsByParent["__none__"] && channelsByParent["__none__"].length > 0 && (
              <div className="card-sm">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm">📂</span>
                  <span className="font-bold text-sm" style={{ color: "var(--faint)" }}>
                    No Category
                  </span>
                </div>
                <div className="space-y-1 ml-4">
                  {channelsByParent["__none__"].map((ch) => (
                    <div
                      key={ch.id}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg"
                      style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
                    >
                      <span className="text-sm">{TYPE_LABELS[ch.type] || "📌"}</span>
                      <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
                        #{ch.name}
                      </span>
                      <button
                        onClick={() => deleteChannel(ch.id)}
                        className="btn btn-danger"
                        style={{ padding: "4px 8px", fontSize: "0.7rem" }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Roles tab */}
        {activeTab === "roles" && (
          <div className="space-y-4 animate-fade">
            <div className="card-sm">
              <h3 className="text-sm font-bold mb-3" style={{ color: "var(--text)" }}>
                + Create Role
              </h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                  placeholder="Role name"
                  className="input flex-1"
                />
                <input
                  type="color"
                  value={newRoleColor}
                  onChange={(e) => setNewRoleColor(e.target.value)}
                  className="w-10 h-10 rounded cursor-pointer"
                  style={{ background: "var(--surface)", border: "1px solid var(--line)" }}
                />
                <button
                  onClick={createRole}
                  disabled={creatingRole || !newRoleName.trim()}
                  className="btn btn-primary"
                >
                  {creatingRole ? "..." : "Create"}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              {data.roles
                .sort((a, b) => b.position - a.position)
                .map((role) => (
                  <div
                    key={role.id}
                    className="card-sm flex items-center gap-3"
                  >
                    <div
                      className="w-8 h-8 rounded-full"
                      style={{
                        background: role.color ? `#${role.color.toString(16).padStart(6, "0")}` : "var(--line)",
                      }}
                    />
                    <div className="flex-1">
                      <div className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                        {role.name}
                      </div>
                      <div className="text-xs" style={{ color: "var(--faint)" }}>
                        Position: {role.position} • Hoist: {role.hoist ? "Yes" : "No"}
                      </div>
                    </div>
                    {role.name !== "@everyone" && (
                      <button
                        onClick={() => deleteRole(role.id)}
                        className="btn btn-danger"
                        style={{ padding: "4px 8px", fontSize: "0.7rem" }}
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Members tab */}
        {activeTab === "members" && (
          <div className="space-y-2 animate-fade">
            {data.members.map((m) => (
              <div
                key={m.user.id}
                className="card-sm flex items-center gap-3"
              >
                {m.user.avatar ? (
                  <img
                    src={`https://cdn.discordapp.com/avatars/${m.user.id}/${m.user.avatar}.png?size=64`}
                    alt={m.user.username}
                    className="w-9 h-9 rounded-full"
                  />
                ) : (
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{ background: "var(--primary-dim)", color: "var(--primary)" }}
                  >
                    {(m.user.display_name || m.user.username).charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1">
                  <div className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                    {m.user.display_name || m.user.username}
                  </div>
                  <div className="text-xs" style={{ color: "var(--faint)" }}>
                    @{m.user.username} • Joined {new Date(m.joined_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex gap-1">
                  {m.roles.slice(0, 3).map((rid) => {
                    const role = data.roles.find((r) => r.id === rid);
                    return role ? (
                      <span
                        key={rid}
                        className="badge"
                        style={{
                          background: role.color
                            ? `#${role.color.toString(16).padStart(6, "0")}20`
                            : "var(--surface3)",
                          color: role.color
                            ? `#${role.color.toString(16).padStart(6, "0")}`
                            : "var(--muted)",
                        }}
                      >
                        {role.name}
                      </span>
                    ) : null;
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
      <JamieChat guildContext={guildContext} />
    </div>
  );
}
