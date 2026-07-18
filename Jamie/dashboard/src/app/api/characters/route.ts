import { NextResponse } from "next/server";
import { getCustomCharacters, addCustomCharacter, deleteCustomCharacter } from "@/lib/jamie-db";

export async function GET(req: Request) {
  try {
    const guildId = new URL(req.url).searchParams.get("guildId");
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }
    const characters = getCustomCharacters(guildId);
    return NextResponse.json({ characters });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const guildId = String(body.guildId || "").trim();
    const name = String(body.name || "").trim();
    const avatarUrl = String(body.avatarUrl || "").trim();
    const systemPrompt = String(body.systemPrompt || "").trim();
    const shortcut = String(body.shortcut || "").trim();

    if (!guildId || !name || !systemPrompt || !shortcut) {
      return NextResponse.json({ error: "Missing required fields (guildId, name, systemPrompt, shortcut)" }, { status: 400 });
    }

    addCustomCharacter(guildId, name, avatarUrl, systemPrompt, shortcut);
    return NextResponse.json({ ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const body = await req.json();
    const guildId = String(body.guildId || "").trim();
    const charId = Number(body.charId);

    if (!guildId || isNaN(charId)) {
      return NextResponse.json({ error: "guildId and numeric charId required" }, { status: 400 });
    }

    const deleted = deleteCustomCharacter(guildId, charId);
    return NextResponse.json({ ok: deleted });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
