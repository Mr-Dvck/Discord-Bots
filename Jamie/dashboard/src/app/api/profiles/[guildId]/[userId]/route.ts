import { NextResponse } from "next/server";
import { getProfile } from "@/lib/jamie-db";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ guildId: string; userId: string }> }
) {
  try {
    const { guildId, userId } = await params;
    const data = getProfile(guildId, userId);
    if (!data.profile) {
      return NextResponse.json(
        { error: "Profile not found", ...data },
        { status: 404 }
      );
    }
    return NextResponse.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
