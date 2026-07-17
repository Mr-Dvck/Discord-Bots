import { NextResponse } from "next/server";
import { getGuildCommandsConfig, setGuildCommandsConfig } from "@/lib/jamie-db";

export async function GET(req: Request) {
  try {
    const guildId = new URL(req.url).searchParams.get("guildId");
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }
    const config = getGuildCommandsConfig(guildId);
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

    const nextConfig = setGuildCommandsConfig(guildId, config);
    return NextResponse.json({ config: nextConfig, ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
