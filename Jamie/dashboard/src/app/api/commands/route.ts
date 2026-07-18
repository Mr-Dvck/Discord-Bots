import { NextResponse } from "next/server";

// Dynamic import to avoid Turbopack resolution issues
async function getDbFunctions() {
  const module = await import("@/lib/jamie-db");
  return {
    getGuildCommandsConfig: module.getGuildCommandsConfig,
    setGuildCommandsConfig: module.setGuildCommandsConfig
  };
}

// Fallback implementations in case exports fail
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
      const { getGuildCommandsConfig } = await getDbFunctions();
      config = getGuildCommandsConfig(guildId);
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
      const { setGuildCommandsConfig } = await getDbFunctions();
      nextConfig = setGuildCommandsConfig(guildId, config);
    } catch {
      nextConfig = fallbackSetConfig(guildId, config);
    }
    
    return NextResponse.json({ config: nextConfig, ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
