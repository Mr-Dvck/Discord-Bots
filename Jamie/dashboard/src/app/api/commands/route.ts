import { NextResponse } from "next/server";

// Use dynamic import to work around Turbopack's static export analysis issues
// on Vercel. jamie-db.ts uses node:sqlite + turbopackIgnore comments which
// confuse the bundler's ability to statically detect named exports.
async function loadCommandsConfig() {
  const mod = await import("@/lib/jamie-db");
  return {
    getGuildCommandsConfig: mod.getGuildCommandsConfig,
    setGuildCommandsConfig: mod.setGuildCommandsConfig,
  };
}

function fallbackGetConfig(guildId: string): Record<string, boolean> {
  return {};
}

function fallbackSetConfig(guildId: string, config: Record<string, boolean>): Record<string, boolean> {
  return config;
}

export async function GET(req: Request) {
  try {
    const guildId = new URL(req.url).searchParams.get("guildId");
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }

    let config: Record<string, boolean> = {};
    try {
      const fns = await loadCommandsConfig();
      if (typeof fns.getGuildCommandsConfig === "function") {
        config = fns.getGuildCommandsConfig(guildId);
      } else {
        config = fallbackGetConfig(guildId);
      }
    } catch {
      config = fallbackGetConfig(guildId);
    }

    return NextResponse.json({ config });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(req: Request) {
  try {
    const body = await req.json();
    const guildId = String(body.guildId || "").trim();
    const config = body.config;
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }
    if (!config || typeof config !== "object") {
      return NextResponse.json({ error: "config object required" }, { status: 400 });
    }

    let nextConfig: Record<string, boolean> = {};
    try {
      const fns = await loadCommandsConfig();
      if (typeof fns.setGuildCommandsConfig === "function") {
        nextConfig = fns.setGuildCommandsConfig(guildId, config);
      } else {
        nextConfig = fallbackSetConfig(guildId, config);
      }
    } catch {
      nextConfig = fallbackSetConfig(guildId, config);
    }

    return NextResponse.json({ config: nextConfig, ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
