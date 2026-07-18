import { NextResponse } from "next/server";
import { getOnboardingRecords } from "@/lib/jamie-db";

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: { guildId: string } }
) {
  try {
    const guildId = params.guildId;

    // Validate guild ID
    if (!guildId || !/^\d+$/.test(guildId)) {
      return NextResponse.json(
        { error: "Invalid guild ID" },
        { status: 400 }
      );
    }

    const records = getOnboardingRecords(guildId);
    return NextResponse.json({ records });
  } catch (error) {
    console.error("Error fetching onboarding records:", error);
    return NextResponse.json(
      { error: "Failed to fetch onboarding records" },
      { status: 500 }
    );
  }
}
