"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
  icon: string | null;
  owner: boolean;
  member_count?: number;
}

export default function ServersPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        setGuilds(Array.isArray(data) ? data : []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = guilds.filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
            🗺️ Servers
          </h1>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search servers..."
            className="input"
            style={{ width: 240 }}
          />
        </div>

        {loading ? (
          <p style={{ color: "var(--faint)" }}>Loading...</p>
        ) : filtered.length === 0 ? (
          <div className="card space-y-3">
            <p style={{ color: "var(--faint)" }}>
              {guilds.length === 0
                ? "No servers found. Invite Jamie with the bot scope so it can join and manage servers."
                : "No servers match your search."}
            </p>
            {guilds.length === 0 && (
              <a
                href="https://discord.com/oauth2/authorize?client_id=1527491367062999111&permissions=8&integration_type=0&scope=bot%20applications.commands"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ textDecoration: "none" }}
              >
                ➕ Invite Jamie to a Server
              </a>
            )}
          </div>
        ) : (
          <div className="grid gap-3">
            {filtered.map((guild) => (
              <Link
                key={guild.id}
                href={`/servers/${guild.id}`}
                className="card-sm flex items-center gap-3 transition-all hover:scale-[1.005]"
                style={{ textDecoration: "none" }}
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
                  <div className="font-semibold text-sm" style={{ color: "var(--text)" }}>
                    {guild.name}
                  </div>
                  <div className="text-xs" style={{ color: "var(--faint)" }}>
                    {guild.owner ? "👑 Owner" : "🛡️ Admin"} • {guild.member_count || "?"} members
                  </div>
                </div>
                <span className="badge badge-core">View</span>
              </Link>
            ))}
          </div>
        )}
      </main>
      <JamieChat />
    </div>
  );
}
