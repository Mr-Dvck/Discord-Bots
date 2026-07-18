import { NextResponse } from "next/server";
import { createRole, deleteRole, modifyRole } from "@/lib/discord";

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
    const role = await createRole(id, body);
    return NextResponse.json(role);
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
    const { roleId, ...data } = body;
    const role = await modifyRole(id, roleId, data);
    return NextResponse.json(role);
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
    const { roleId } = body;
    await deleteRole(id, roleId);
    return NextResponse.json({ success: true });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
