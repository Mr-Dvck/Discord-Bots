import { NextResponse } from "next/server";
import { getGuildCommandsConfig, setGuildCommandsConfig } from "@/lib/jamie-db";

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
    const config = getGuildCommandsConfig ? getGuildCommandsConfig(guildId) : fallbackGetConfig(guildId);
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

    const nextConfig = setGuildCommandsConfig ? setGuildCommandsConfig(guildId, config) : fallbackSetConfig(guildId, config);
    return NextResponse.json({ config: nextConfig, ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
