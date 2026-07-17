import { NextResponse } from "next/server";
import { getStarboardConfig, setStarboardConfig } from "@/lib/jamie-db";

export async function GET(req: Request) {
  try {
    const guildId = new URL(req.url).searchParams.get("guildId");
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }
    const config = getStarboardConfig(guildId);
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
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }

    const patch: Parameters<typeof setStarboardConfig>[1] = {};
    if (typeof body.enabled === "boolean") patch.enabled = body.enabled;
    if (body.channel_id !== undefined) {
      patch.channel_id = body.channel_id ? String(body.channel_id) : null;
    }
    if (typeof body.min_stars === "number") patch.min_stars = body.min_stars;

    const config = setStarboardConfig(guildId, patch);
    return NextResponse.json({ config, ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
