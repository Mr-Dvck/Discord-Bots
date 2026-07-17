import { NextResponse } from "next/server";
import { getWelcomeConfig, setWelcomeConfig } from "@/lib/jamie-db";

export async function GET(req: Request) {
  try {
    const guildId = new URL(req.url).searchParams.get("guildId");
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }
    const config = getWelcomeConfig(guildId);
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

    const patch: Parameters<typeof setWelcomeConfig>[1] = {};
    if (typeof body.enabled === "boolean") patch.enabled = body.enabled;
    if (body.channel_id !== undefined) {
      patch.channel_id = body.channel_id ? String(body.channel_id) : null;
    }
    if (typeof body.message === "string") patch.message = body.message;
    if (typeof body.image_line === "string") patch.image_line = body.image_line;
    if (typeof body.dm_on_join === "boolean") patch.dm_on_join = body.dm_on_join;
    if (typeof body.background_path === "string") {
      patch.background_path = body.background_path;
    }

    // Enabling with a channel is the normal dashboard flow
    if (patch.enabled && patch.channel_id === undefined) {
      const cur = getWelcomeConfig(guildId);
      if (!cur.channel_id && !patch.channel_id) {
        // allow enable=false freely; enable=true without channel still saves
      }
    }

    const config = setWelcomeConfig(guildId, patch);
    return NextResponse.json({ config, ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
