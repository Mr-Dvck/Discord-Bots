import { NextResponse } from "next/server";
import { buildServer, ServerBlueprint } from "@/lib/discord";

function isValidSnowflake(id: string): boolean {
  return /^\d{17,20}$/.test(id.trim());
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // Validate guild_id is a proper snowflake (not a channel ID)
  if (!isValidSnowflake(id)) {
    return NextResponse.json({
      error: `Invalid server ID "${id}". Must be a 17-20 digit server snowflake, not a channel ID.`
    }, { status: 400 });
  }

  try {
    const blueprint: ServerBlueprint = await req.json();
    const results = await buildServer(id, blueprint);
    return NextResponse.json(results);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
