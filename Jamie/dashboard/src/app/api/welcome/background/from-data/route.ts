import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";
import { setWelcomeConfig, welcomeBgDir } from "@/lib/jamie-db";

/**
 * Save an already-generated Image Studio PNG as the Welcome module background.
 * Names are applied by the bot on join — not in the studio.
 */
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const guildId = String(body.guildId || "").trim();
    const dataUrl = String(body.dataUrl || "");
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }
    if (!dataUrl.startsWith("data:image/")) {
      return NextResponse.json({ error: "dataUrl image required" }, { status: 400 });
    }

    const comma = dataUrl.indexOf(",");
    if (comma < 0) {
      return NextResponse.json({ error: "Invalid dataUrl" }, { status: 400 });
    }
    const b64 = dataUrl.slice(comma + 1);
    const buf = Buffer.from(b64, "base64");
    if (buf.length < 500) {
      return NextResponse.json({ error: "Image too small" }, { status: 400 });
    }

    const dir = welcomeBgDir();
    fs.mkdirSync(dir, { recursive: true });
    const filePath = path.join(dir, `${guildId}.png`);
    fs.writeFileSync(filePath, buf);

    const config = setWelcomeConfig(guildId, { background_path: filePath });

    return NextResponse.json({ ok: true, path: filePath, config });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
