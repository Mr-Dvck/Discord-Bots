import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";
import { generateImage } from "@/lib/image";
import { setWelcomeConfig, welcomeBgDir } from "@/lib/jamie-db";

export const maxDuration = 120;

const DEFAULT_PROMPT =
  "Dark cyberpunk Discord welcome banner background for a server called Certified, " +
  "neon cyan and lime accents, gritty metal and night energy, cinematic wide composition, " +
  "empty lower third for text overlay, high detail, NO text, NO letters, NO watermarks";

/**
 * Generate once + store as the server's welcome background module asset.
 * Joins use this file — no AI per join.
 */
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const guildId = String(body.guildId || "").trim();
    if (!guildId) {
      return NextResponse.json({ error: "guildId required" }, { status: 400 });
    }

    const prompt = String(body.prompt || DEFAULT_PROMPT).trim();
    const result = await generateImage({
      prompt,
      size: "welcome",
      enhance: body.enhance !== false,
    });

    const dir = welcomeBgDir();
    /*turbopackIgnore: true*/ fs.mkdirSync(dir, { recursive: true });
    const filePath = /*turbopackIgnore: true*/ path.join(dir, `${guildId}.png`);
    /*turbopackIgnore: true*/ fs.writeFileSync(filePath, Buffer.from(result.base64, "base64"));

    const config = setWelcomeConfig(guildId, { background_path: filePath });

    return NextResponse.json({
      ok: true,
      path: filePath,
      dataUrl: result.dataUrl,
      config,
    });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
