"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
  owner: boolean;
  member_count?: number;
}

export default function DashboardPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [apiOnline, setApiOnline] = useState(false);

  // Bot application ID (same as bot user for standard bots)
  const inviteUrl =
    "https://discord.com/oauth2/authorize?client_id=1527491367062999111&permissions=8&integration_type=0&scope=bot%20applications.commands";

  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        setGuilds(Array.isArray(data) ? data : []);
        setApiOnline(true);
      })
      .catch((e) => {
        setError(e.message);
        setApiOnline(false);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalMembers = guilds.reduce(
    (sum, g) => sum + (g.member_count || 0),
    0
  );

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main
        className="flex-1 ml-[240px] p-8"
        style={{ background: "var(--bg)" }}
      >
        {/* Hero */}
        <div className="card mb-6 animate-fade">
          <div className="flex items-center gap-4 mb-4">
            <div
              className="flex items-center justify-center rounded-xl text-2xl"
              style={{
                width: 52,
                height: 52,
                background: "var(--primary-dim)",
                border: "1px solid rgba(57,183,196,0.3)",
              }}
            >
              🔥
            </div>
            <div>
              <h1
                className="text-2xl font-bold"
                style={{ color: "var(--primary)" }}
              >
                Jamie Dashboard
              </h1>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Manage your servers, modules, and talk to Jamie
              </p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div
          className="grid grid-cols-3 gap-4 mb-6"
          style={{ gridTemplateColumns: "repeat(3, 1fr)" }}
        >
          <div className="card-sm animate-fade">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-1"
              style={{ color: "var(--faint)" }}
            >
              Servers
            </div>
            <div
              className="text-3xl font-bold"
              style={{ color: "var(--primary)" }}
            >
              {guilds.length}
            </div>
          </div>
          <div className="card-sm animate-fade">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-1"
              style={{ color: "var(--faint)" }}
            >
              Total Members
            </div>
            <div
              className="text-3xl font-bold"
              style={{ color: "var(--accent)" }}
            >
              {totalMembers.toLocaleString()}
            </div>
          </div>
          <div className="card-sm animate-fade">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-1"
              style={{ color: "var(--faint)" }}
            >
              Status
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  background: loading
                    ? "var(--warn)"
                    : apiOnline
                      ? "var(--accent)"
                      : "var(--danger)",
                }}
              />
              <span
                className="text-lg font-bold"
                style={{
                  color: loading
                    ? "var(--warn)"
                    : apiOnline
                      ? "var(--accent)"
                      : "var(--danger)",
                }}
              >
                {loading ? "Checking..." : apiOnline ? "Online" : "Offline"}
              </span>
            </div>
          </div>
        </div>

        {/* Server list */}
        <div className="card animate-fade">
          <h2
            className="text-lg font-bold mb-4"
            style={{ color: "var(--text)" }}
          >
            🗺️ Your Servers
          </h2>

          {loading && (
            <p style={{ color: "var(--faint)" }}>Loading servers...</p>
          )}
          {error && (
            <p style={{ color: "var(--danger)" }}>Error: {error}</p>
          )}

          {!loading && !error && guilds.length === 0 && (
            <div className="space-y-3">
              <p style={{ color: "var(--faint)" }}>
                No servers found. Jamie isn&apos;t in any Discord servers yet.
                Invite the bot with the <strong>bot</strong> scope (not
                commands-only) so the dashboard can manage channels and roles.
              </p>
              <a
                href={inviteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ textDecoration: "none" }}
              >
                ➕ Invite Jamie to a Server
              </a>
            </div>
          )}

          <div className="space-y-2">
            {guilds.map((guild) => (
              <a
                key={guild.id}
                href={`/servers/${guild.id}`}
                className="flex items-center gap-3 px-4 py-3 rounded-lg transition-all hover:scale-[1.01]"
                style={{
                  background: "var(--surface2)",
                  border: "1px solid var(--line)",
                }}
              >
                {guild.icon ? (
                  <img
                    src={`https://cdn.discordapp.com/icons/${guild.id}/${guild.icon}.png?size=64`}
                    alt={guild.name}
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <div
                    className="flex items-center justify-center rounded-full text-sm font-bold"
                    style={{
                      width: 40,
                      height: 40,
                      background: "var(--primary-dim)",
                      color: "var(--primary)",
                    }}
                  >
                    {guild.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1">
                  <div
                    className="font-semibold text-sm"
                    style={{ color: "var(--text)" }}
                  >
                    {guild.name}
                  </div>
                  <div className="text-xs" style={{ color: "var(--faint)" }}>
                    {guild.owner ? "👑 Owner" : "🛡️ Admin"} •{" "}
                    {guild.member_count || "?"} members
                  </div>
                </div>
                <span style={{ color: "var(--faint)" }}>→</span>
              </a>
            ))}
          </div>
        </div>

        {/* Quick actions */}
        <div
          className="grid gap-4 mt-6"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}
        >
          <a
            href="/images"
            className="card flex items-center gap-4 transition-all hover:scale-[1.01] cursor-pointer"
            style={{ textDecoration: "none" }}
          >
            <div
              className="flex items-center justify-center rounded-xl text-xl"
              style={{
                width: 44,
                height: 44,
                background: "var(--premium-dim)",
                border: "1px solid rgba(217,138,255,0.3)",
              }}
            >
              🎨
            </div>
            <div>
              <div
                className="font-bold text-sm"
                style={{ color: "var(--premium)" }}
              >
                Images
              </div>
              <div className="text-xs" style={{ color: "var(--faint)" }}>
                Welcome banners & art
              </div>
            </div>
          </a>
          <a
            href="/commands"
            className="card flex items-center gap-4 transition-all hover:scale-[1.01] cursor-pointer"
            style={{ textDecoration: "none" }}
          >
            <div
              className="flex items-center justify-center rounded-xl text-xl"
              style={{
                width: 44,
                height: 44,
                background: "var(--primary-dim)",
                border: "1px solid rgba(57,183,196,0.3)",
              }}
            >
              ⌨️
            </div>
            <div>
              <div
                className="font-bold text-sm"
                style={{ color: "var(--primary)" }}
              >
                Commands
              </div>
              <div className="text-xs" style={{ color: "var(--faint)" }}>
                Browse all slash packs
              </div>
            </div>
          </a>
          <a
            href="/builder"
            className="card flex items-center gap-4 transition-all hover:scale-[1.01] cursor-pointer"
            style={{ textDecoration: "none" }}
          >
            <div
              className="flex items-center justify-center rounded-xl text-xl"
              style={{
                width: 44,
                height: 44,
                background: "var(--premium-dim)",
                border: "1px solid rgba(217,138,255,0.3)",
              }}
            >
              🏗️
            </div>
            <div>
              <div
                className="font-bold text-sm"
                style={{ color: "var(--premium)" }}
              >
                Server Builder
              </div>
              <div className="text-xs" style={{ color: "var(--faint)" }}>
                Build or revamp entire servers
              </div>
            </div>
          </a>
          <a
            href="/modules"
            className="card flex items-center gap-4 transition-all hover:scale-[1.01] cursor-pointer"
            style={{ textDecoration: "none" }}
          >
            <div
              className="flex items-center justify-center rounded-xl text-xl"
              style={{
                width: 44,
                height: 44,
                background: "var(--warn-dim)",
                border: "1px solid rgba(240,179,90,0.3)",
              }}
            >
              ⚙️
            </div>
            <div>
              <div
                className="font-bold text-sm"
                style={{ color: "var(--warn)" }}
              >
                Modules
              </div>
              <div className="text-xs" style={{ color: "var(--faint)" }}>
                Toggle command packs
              </div>
            </div>
          </a>
        </div>
      </main>

      <JamieChat />
    </div>
  );
}
