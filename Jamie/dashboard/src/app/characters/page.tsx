"use client";

import { useState, useEffect, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

interface Guild {
  id: string;
  name: string;
}

interface CustomCharacter {
  id: number;
  guild_id: string;
  name: string;
  avatar_url: string;
  system_prompt: string;
  shortcut: string;
  created_at: string;
}

export default function CharactersPage() {
  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [selectedGuild, setSelectedGuild] = useState("");
  const [characters, setCharacters] = useState<CustomCharacter[]>([]);
  const [loading, setLoading] = useState(false);

  // New character form state
  const [name, setName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [shortcut, setShortcut] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Fetch servers list
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

  // Fetch characters list
  const loadCharacters = useCallback(async (guildId: string) => {
    if (!guildId) return;
    setLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`/api/characters?guildId=${encodeURIComponent(guildId)}`);
      const data = await res.json();
      if (data.characters) {
        setCharacters(data.characters);
      } else {
        setCharacters([]);
      }
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedGuild) {
      loadCharacters(selectedGuild);
    } else {
      setCharacters([]);
    }
  }, [selectedGuild, loadCharacters]);

  // Create character
  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedGuild) {
      setErrorMsg("Select a server first.");
      return;
    }
    if (!name.trim() || !shortcut.trim() || !systemPrompt.trim()) {
      setErrorMsg("All fields except Avatar URL are required.");
      return;
    }

    setSubmitting(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const res = await fetch("/api/characters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guildId: selectedGuild,
          name,
          avatarUrl: avatarUrl.trim() || "https://i.imgur.com/3Z8m3yE.png",
          systemPrompt,
          shortcut,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Failed to create character");

      setSuccessMsg(`Character "${name}" created successfully!`);
      setName("");
      setAvatarUrl("");
      setShortcut("");
      setSystemPrompt("");
      loadCharacters(selectedGuild);
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  // Delete character
  async function handleDelete(charId: number) {
    if (!confirm("Are you sure you want to delete this character?")) return;
    setErrorMsg("");
    setSuccessMsg("");
    try {
      const res = await fetch("/api/characters", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guildId: selectedGuild, charId }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Failed to delete");
      setSuccessMsg("Character deleted.");
      loadCharacters(selectedGuild);
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        {/* Header & Server Selector */}
        <div className="flex flex-wrap items-center justify-between gap-6 mb-8 pb-6" style={{ borderBottom: "1px solid var(--line)" }}>
          <div>
            <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
              🎭 Custom Characters
            </h1>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Create multiple AI personalities with unique names, avatars, and triggers.
            </p>
          </div>

          <select
            className="select"
            value={selectedGuild}
            onChange={(e) => setSelectedGuild(e.target.value)}
            style={{ minWidth: 220 }}
          >
            <option value="">Select Server…</option>
            {guilds.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>

        {/* Notifications */}
        {errorMsg && (
          <div className="p-3 mb-6 rounded-lg text-sm bg-[rgba(240,71,71,0.15)] text-[var(--danger)] border border-[rgba(240,71,71,0.3)] animate-fade">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="p-3 mb-6 rounded-lg text-sm bg-[rgba(125,211,167,0.15)] text-[var(--ok)] border border-[rgba(125,211,167,0.3)] animate-fade">
            {successMsg}
          </div>
        )}

        <div className="grid gap-8 grid-cols-1 lg:grid-cols-12">
          {/* Creator Form */}
          <div className="lg:col-span-5">
            <form onSubmit={handleCreate} className="card space-y-4">
              <h2 className="text-base font-bold mb-2">✨ Create New Character</h2>

              <div>
                <label className="label text-xs font-semibold uppercase mb-1">Character Name</label>
                <input
                  type="text"
                  placeholder="e.g. Cynthia"
                  className="input w-full"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={!selectedGuild}
                />
              </div>

              <div>
                <label className="label text-xs font-semibold uppercase mb-1">Shortcut Prefix</label>
                <input
                  type="text"
                  placeholder="e.g. cynthia"
                  className="input w-full"
                  value={shortcut}
                  onChange={(e) => setShortcut(e.target.value)}
                  disabled={!selectedGuild}
                />
                <span className="text-xs" style={{ color: "var(--faint)" }}>
                  Trigger character by starting a message with <code>{shortcut || "shortcut"}: </code> or pinging them
                </span>
              </div>

              <div>
                <label className="label text-xs font-semibold uppercase mb-1">Avatar Image URL</label>
                <input
                  type="text"
                  placeholder="Link to avatar image (PNG/JPG)"
                  className="input w-full"
                  value={avatarUrl}
                  onChange={(e) => setAvatarUrl(e.target.value)}
                  disabled={!selectedGuild}
                />
              </div>

              <div>
                <label className="label text-xs font-semibold uppercase mb-1">Personality System Prompt</label>
                <textarea
                  placeholder="Describe how they think, speak, and act. Example: You are Cynthia, a highly analytical, snarky Discord moderator. Keep replies short."
                  className="textarea w-full"
                  rows={6}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  disabled={!selectedGuild}
                />
              </div>

              <button
                type="submit"
                className="btn btn-accent w-full"
                disabled={submitting || !selectedGuild}
              >
                {submitting ? "Creating…" : "Save Character"}
              </button>
            </form>
          </div>

          {/* Roster Listing */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold">👥 Current Roster ({characters.length})</h2>
            </div>

            {loading ? (
              <div className="card text-center py-8">
                <span className="text-sm" style={{ color: "var(--faint)" }}>Loading roster…</span>
              </div>
            ) : characters.length === 0 ? (
              <div className="card text-center py-8">
                <p style={{ color: "var(--faint)" }}>
                  {selectedGuild ? "No custom characters created yet." : "Select a server at the top to view its characters."}
                </p>
              </div>
            ) : (
              <div className="grid gap-4">
                {characters.map((char) => (
                  <div
                    key={char.id}
                    className="card flex flex-col md:flex-row md:items-start gap-4 hover:border-[var(--primary)] transition-all"
                  >
                    {/* Character Avatar */}
                    <img
                      src={char.avatar_url}
                      alt={char.name}
                      className="w-12 h-12 rounded-full object-cover shrink-0 border border-slate-700 bg-slate-800"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "https://i.imgur.com/3Z8m3yE.png";
                      }}
                    />

                    {/* Character Info */}
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-bold text-sm" style={{ color: "var(--text)" }}>{char.name}</h3>
                        <span className="badge badge-core">prefix: {char.shortcut}:</span>
                      </div>

                      <p className="text-xs" style={{ color: "var(--muted)", whiteSpace: "pre-wrap" }}>
                        {char.system_prompt}
                      </p>
                    </div>

                    {/* Actions */}
                    <button
                      onClick={() => handleDelete(char.id)}
                      className="btn text-xs text-[var(--danger)] hover:bg-[rgba(240,71,71,0.1)] border border-[rgba(240,71,71,0.3)] md:self-start shrink-0"
                      style={{ padding: "4px 10px" }}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
      <JamieChat
        guildId={selectedGuild || undefined}
        guildContext={
          selectedGuild
            ? `Viewing custom characters roster for server ${guilds.find((g) => g.id === selectedGuild)?.name || ""} (${selectedGuild}).`
            : ""
        }
      />
    </div>
  );
}
