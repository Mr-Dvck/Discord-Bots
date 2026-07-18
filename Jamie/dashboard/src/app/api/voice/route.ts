import { NextResponse } from "next/server";
import { discordRequest } from "@/lib/discord";

function isValidSnowflake(id: string): boolean {
  return /^\d{17,20}$/.test(id.trim());
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, guild_id, channel_id } = body;

    if (!guild_id) {
      return NextResponse.json({ error: "guild_id required" }, { status: 400 });
    }

    // Validate guild_id is a proper snowflake (not a channel ID)
    if (!isValidSnowflake(guild_id)) {
      return NextResponse.json({ 
        error: `Invalid guild_id "${guild_id}". Must be a 17-20 digit server snowflake, not a channel ID.` 
      }, { status: 400 });
    }

    if (action === "join") {
      if (!channel_id) {
        return NextResponse.json({ error: "channel_id required for join" }, { status: 400 });
      }

      // Validate channel_id is a proper snowflake
      if (!isValidSnowflake(channel_id)) {
        return NextResponse.json({ 
          error: `Invalid channel_id "${channel_id}". Must be a 17-20 digit channel snowflake.` 
        }, { status: 400 });
      }

      const result = await discordRequest("POST", `/guilds/${guild_id}/voice-states/@me`, {
        channel_id: channel_id,
      });

      return NextResponse.json({ 
        success: true, 
        action: "joined", 
        guild_id, 
        channel_id,
        result 
      });
    } else if (action === "leave") {
      const result = await discordRequest("DELETE", `/guilds/${guild_id}/voice-states/@me`);

      return NextResponse.json({ 
        success: true, 
        action: "left", 
        guild_id,
        result 
      });
    } else {
      return NextResponse.json({ error: "action must be 'join' or 'leave'" }, { status: 400 });
    }
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
