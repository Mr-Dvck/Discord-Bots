"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import JamieChat from "@/components/JamieChat";

type ImageSize = "square" | "welcome" | "banner" | "portrait" | "story";

const SIZES: { id: ImageSize; label: string; hint: string }[] = [
  { id: "welcome", label: "Welcome", hint: "1280×720 — join banners" },
  { id: "banner", label: "Banner", hint: "1500×500 — headers" },
  { id: "square", label: "Square", hint: "1024×1024 — icons / posts" },
  { id: "portrait", label: "Portrait", hint: "768×1024 — posters" },
  { id: "story", label: "Story", hint: "768×1344 — tall" },
];

const PRESETS: { label: string; prompt: string; size: ImageSize }[] = [
  {
    label: "Welcome banner",
    size: "welcome",
    prompt:
      "Dark cyberpunk Discord welcome banner, neon cyan and lime, text space on the left, abstract metal geometry, high detail, no words",
  },
  {
    label: "Certified vibe",
    size: "welcome",
    prompt:
      "Gritty underground nightclub aesthetic, teal neon, cracked concrete, digital glitch, chaotic energy, cinematic lighting, no text",
  },
  {
    label: "Jamie face card",
    size: "square",
    prompt:
      "Stylized portrait of a 19 year old chaotic genius with fire eyes, dark streetwear, metallic teal accents, high detail illustration",
  },
  {
    label: "Server rules art",
    size: "portrait",
    prompt:
      "Dark fantasy plaque background for Discord rules, ornate black metal frame, teal glow, empty center for text, atmospheric",
  },
  {
    label: "VC lobby",
    size: "banner",
    prompt:
      "Wide horizontal Discord banner, sound waves and headphones, dark void with cyan light streaks, clean modern, no text",
  },
];

interface Guild {
  id: string;
  name: string;
}

interface Channel {
  id: string;
  name: string;
  type: number;
  parent_id: string | null;
}

export default function ImagesPage() {
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  const [size, setSize] = useState<ImageSize>("welcome");
  const [enhance, setEnhance] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{
    dataUrl: string;
    enhancedPrompt: string;
    prompt: string;
    width: number;
    height: number;
  } | null>(null);

  const [guilds, setGuilds] = useState<Guild[]>([]);
  const [guildId, setGuildId] = useState("");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelId, setChannelId] = useState("");
  const [posting, setPosting] = useState(false);
  const [postMsg, setPostMsg] = useState("");

  useEffect(() => {
    fetch("/api/guilds")
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) setGuilds(data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!guildId) {
      setChannels([]);
      setChannelId("");
      return;
    }
    fetch(`/api/guilds/${guildId}`)
      .then((r) => r.json())
      .then((data) => {
        const ch = Array.isArray(data.channels) ? data.channels : [];
        setChannels(ch.filter((c: Channel) => c.type === 0));
      })
      .catch(() => setChannels([]));
  }, [guildId]);

  async function generate() {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    setPostMsg("");
    try {
      const res = await fetch("/api/generate-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim(), size, enhance }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Generation failed");
      setResult({
        dataUrl: data.dataUrl,
        enhancedPrompt: data.enhancedPrompt,
        prompt: data.prompt,
        width: data.width,
        height: data.height,
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function postToDiscord() {
    if (!result || !channelId || posting) return;
    setPosting(true);
    setPostMsg("");
    try {
      // Discord needs a hosted URL or multipart; we send via bot as file using a short-lived approach:
      // upload is not available from pure JSON send_message. Use a temporary pollinations re-gen is bad.
      // Instead: post message with the enhanced prompt + dashboard note, and attach via Discord attachment API.
      const res = await fetch("/api/post-image", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channelId,
          dataUrl: result.dataUrl,
          caption: result.prompt,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Post failed");
      setPostMsg("Posted to Discord.");
    } catch (e: unknown) {
      setPostMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setPosting(false);
    }
  }

  function download() {
    if (!result) return;
    const a = document.createElement("a");
    a.href = result.dataUrl;
    a.download = `jamie-${size}-${Date.now()}.png`;
    a.click();
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[240px] p-8" style={{ background: "var(--bg)" }}>
        <div className="mb-6">
          <h1 className="text-xl font-bold" style={{ color: "var(--text)" }}>
            🎨 Image Studio
          </h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Same stack as Discord{" "}
            <code style={{ color: "var(--primary)" }}>/generate</code> — type words,
            get an image (Pollinations flux + optional LLM enhance)
          </p>
        </div>

        <div
          className="grid gap-6"
          style={{ gridTemplateColumns: "minmax(280px, 420px) 1fr" }}
        >
          {/* Controls */}
          <div className="space-y-4">
            <div className="card">
              <label
                className="text-xs font-semibold uppercase tracking-wider mb-2 block"
                style={{ color: "var(--faint)" }}
              >
                Prompt
              </label>
              <textarea
                className="input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={6}
                placeholder="Welcome banner for Certified, teal neon, dark void…"
                style={{ resize: "vertical", minHeight: 120 }}
              />

              <div className="flex flex-wrap gap-2 mt-3">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    type="button"
                    className="btn btn-ghost"
                    style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                    onClick={() => {
                      setPrompt(p.prompt);
                      setSize(p.size);
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="card-sm space-y-3">
              <div
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: "var(--faint)" }}
              >
                Size
              </div>
              <div className="flex flex-wrap gap-2">
                {SIZES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    className="btn"
                    onClick={() => setSize(s.id)}
                    style={{
                      fontSize: "0.8rem",
                      padding: "6px 12px",
                      background:
                        size === s.id ? "var(--primary-dim)" : "transparent",
                      color: size === s.id ? "var(--primary)" : "var(--muted)",
                      border:
                        size === s.id
                          ? "1px solid rgba(57,183,196,0.35)"
                          : "1px solid var(--line)",
                    }}
                    title={s.hint}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              <label
                className="flex items-center gap-2 text-sm cursor-pointer"
                style={{ color: "var(--muted)" }}
              >
                <input
                  type="checkbox"
                  checked={enhance}
                  onChange={(e) => setEnhance(e.target.checked)}
                />
                Enhance prompt with LLM (same as Discord)
              </label>
            </div>

            <button
              type="button"
              className="btn btn-primary w-full"
              disabled={loading || !prompt.trim()}
              onClick={generate}
              style={{ justifyContent: "center", width: "100%" }}
            >
              {loading ? "Generating…" : "Generate image"}
            </button>

            {error && (
              <p className="text-sm" style={{ color: "var(--danger)" }}>
                {error}
              </p>
            )}

            {result && (
              <div className="card-sm space-y-3">
                <div className="flex gap-2 flex-wrap">
                  <button type="button" className="btn btn-accent" onClick={download}>
                    Download PNG
                  </button>
                </div>

                <div
                  className="text-xs font-semibold uppercase"
                  style={{ color: "var(--faint)" }}
                >
                  Post to Discord
                </div>
                <select
                  className="select"
                  value={guildId}
                  onChange={(e) => setGuildId(e.target.value)}
                >
                  <option value="">Select server…</option>
                  {guilds.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
                <select
                  className="select"
                  value={channelId}
                  onChange={(e) => setChannelId(e.target.value)}
                  disabled={!guildId}
                >
                  <option value="">Select channel…</option>
                  {channels.map((c) => (
                    <option key={c.id} value={c.id}>
                      #{c.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={!channelId || posting}
                  onClick={postToDiscord}
                >
                  {posting ? "Posting…" : "Post image as Jamie"}
                </button>
                {postMsg && (
                  <p
                    className="text-xs"
                    style={{
                      color: postMsg.includes("Posted")
                        ? "var(--accent)"
                        : "var(--danger)",
                    }}
                  >
                    {postMsg}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Preview */}
          <div className="card min-h-[360px] flex flex-col">
            <div
              className="text-xs font-semibold uppercase tracking-wider mb-3"
              style={{ color: "var(--faint)" }}
            >
              Preview
            </div>
            {!result && !loading && (
              <div
                className="flex-1 flex items-center justify-center rounded-lg text-sm"
                style={{
                  background: "var(--surface)",
                  border: "1px dashed var(--line)",
                  color: "var(--faint)",
                  minHeight: 320,
                }}
              >
                Your image shows up here
              </div>
            )}
            {loading && (
              <div
                className="flex-1 flex items-center justify-center rounded-lg text-sm animate-pulse"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--line)",
                  color: "var(--primary)",
                  minHeight: 320,
                }}
              >
                Cooking with flux…
              </div>
            )}
            {result && (
              <div className="space-y-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={result.dataUrl}
                  alt={result.prompt}
                  className="w-full rounded-lg"
                  style={{
                    border: "1px solid var(--line)",
                    maxHeight: 560,
                    objectFit: "contain",
                    background: "#0a0e12",
                  }}
                />
                <div className="text-xs space-y-1" style={{ color: "var(--muted)" }}>
                  <div>
                    <strong style={{ color: "var(--text)" }}>You:</strong>{" "}
                    {result.prompt}
                  </div>
                  {result.enhancedPrompt !== result.prompt && (
                    <div>
                      <strong style={{ color: "var(--premium)" }}>Enhanced:</strong>{" "}
                      {result.enhancedPrompt}
                    </div>
                  )}
                  <div style={{ color: "var(--faint)" }}>
                    {result.width}×{result.height}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      <JamieChat guildContext="User is in Image Studio generating welcome/banner art for Discord." />
    </div>
  );
}
