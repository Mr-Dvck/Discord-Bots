import { NextResponse } from "next/server";

const DISCORD_API = "https://discord.com/api/v10";

/**
 * Post a base64 PNG from the dashboard to a Discord channel as Jamie.
 * Uses multipart/form-data attachment upload (bot token).
 */
export async function POST(req: Request) {
  try {
    const token = process.env.DISCORD_BOT_TOKEN_JAMIE;
    if (!token) {
      return NextResponse.json(
        { error: "DISCORD_BOT_TOKEN_JAMIE not set" },
        { status: 500 }
      );
    }

    const body = await req.json();
    const channelId = String(body.channelId || "");
    const dataUrl = String(body.dataUrl || "");
    const caption = String(body.caption || "Generated with Jamie Image Studio").slice(
      0,
      500
    );

    if (!channelId || !dataUrl.startsWith("data:image/")) {
      return NextResponse.json(
        { error: "channelId and image dataUrl required" },
        { status: 400 }
      );
    }

    const comma = dataUrl.indexOf(",");
    if (comma < 0) {
      return NextResponse.json({ error: "Invalid dataUrl" }, { status: 400 });
    }
    const meta = dataUrl.slice(0, comma);
    const b64 = dataUrl.slice(comma + 1);
    const isPng = meta.includes("png");
    const buf = Buffer.from(b64, "base64");
    if (buf.length < 500) {
      return NextResponse.json({ error: "Image too small" }, { status: 400 });
    }

    const form = new FormData();
    const bytes = new Uint8Array(buf);
    const blob = new Blob([bytes], { type: isPng ? "image/png" : "image/jpeg" });
    form.append(
      "files[0]",
      blob,
      isPng ? "jamie_studio.png" : "jamie_studio.jpg"
    );
    form.append(
      "payload_json",
      JSON.stringify({
        content: `🎨 **Image Studio**\n${caption}`,
      })
    );

    const res = await fetch(`${DISCORD_API}/channels/${channelId}/messages`, {
      method: "POST",
      headers: {
        Authorization: `Bot ${token}`,
      },
      body: form,
      cache: "no-store",
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json(
        { error: `Discord ${res.status}: ${err.slice(0, 200)}` },
        { status: 500 }
      );
    }

    const msg = await res.json();
    return NextResponse.json({ ok: true, id: msg.id, channel_id: channelId });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
