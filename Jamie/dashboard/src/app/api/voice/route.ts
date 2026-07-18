import { NextResponse } from "next/server";
import { discordRequest } from "@/lib/discord";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { action, guild_id, channel_id } = body;

    if (!guild_id) {
      return NextResponse.json({ error: "guild_id required" }, { status: 400 });
    }

    if (action === "join") {
      if (!channel_id) {
        return NextResponse.json({ error: "channel_id required for join" }, { status: 400 });
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