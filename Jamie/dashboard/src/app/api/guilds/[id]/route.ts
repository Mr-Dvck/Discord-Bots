import { NextResponse } from "next/server";
import { getGuild, getGuildChannels, getGuildRoles, getGuildMembers } from "@/lib/discord";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const [guild, channels, roles, members] = await Promise.all([
      getGuild(id),
      getGuildChannels(id),
      getGuildRoles(id),
      getGuildMembers(id, 100),
    ]);
    return NextResponse.json({ guild, channels, roles, members });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
