import { NextResponse } from "next/server";
import { createChannel, deleteChannel, modifyChannel } from "@/lib/discord";

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
    const body = await req.json();
    const channel = await createChannel(id, body);
    return NextResponse.json(channel);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}

export async function PATCH(
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
    const body = await req.json();
    const { channelId, ...data } = body;
    const channel = await modifyChannel(channelId, data);
    return NextResponse.json(channel);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}

export async function DELETE(
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
    const body = await req.json();
    const { channelId } = body;
    const result = await deleteChannel(channelId);
    return NextResponse.json({ success: true });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
