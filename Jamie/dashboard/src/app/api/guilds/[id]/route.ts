import { NextResponse } from "next/server";
import { getGuild, getGuildChannels, getGuildRoles, getGuildMembers } from "@/lib/discord";

function isValidSnowflake(id: string): boolean {
  return /^\d{17,20}$/.test(id.trim());
}

export async function GET(
  _req: Request,
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
