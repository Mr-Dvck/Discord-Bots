import { NextResponse } from "next/server";
import { getGuild, getGuildChannels, getGuildRoles, getGuildMembers } from "@/lib/discord";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    // Members requires GUILD_MEMBERS intent — don't fail the whole page if it errors
    const [guild, channels, roles, membersResult] = await Promise.all([
      getGuild(id),
      getGuildChannels(id),
      getGuildRoles(id),
      getGuildMembers(id, 100).catch(() => []),
    ]);

    const memberCount =
      guild?.approximate_member_count ??
      guild?.member_count ??
      (Array.isArray(membersResult) ? membersResult.length : 0);

    return NextResponse.json({
      guild: {
        ...guild,
        member_count: memberCount,
      },
      channels,
      roles,
      members: Array.isArray(membersResult) ? membersResult : [],
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
