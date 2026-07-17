import { NextResponse } from "next/server";
import { listProfiles } from "@/lib/jamie-db";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const url = new URL(req.url);
    const guildId = url.searchParams.get("guildId") || undefined;
    const search = url.searchParams.get("q") || undefined;
    const limit = Number(url.searchParams.get("limit") || "200");

    const data = listProfiles({ guildId, search, limit });
    return NextResponse.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message, profiles: [], total: 0 }, { status: 500 });
  }
}
