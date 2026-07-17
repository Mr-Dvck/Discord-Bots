import { NextResponse } from "next/server";
import { getGuilds } from "@/lib/discord";

export async function GET() {
  try {
    const guilds = await getGuilds();
    return NextResponse.json(guilds);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
