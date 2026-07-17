import { NextResponse } from "next/server";
import { generateImage, IMAGE_SIZES, type ImageSize } from "@/lib/image";

export const maxDuration = 120;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const prompt = String(body.prompt || "").trim();
    if (!prompt) {
      return NextResponse.json({ error: "Prompt required" }, { status: 400 });
    }

    const size = (body.size as ImageSize) || "square";
    if (!IMAGE_SIZES[size]) {
      return NextResponse.json({ error: "Invalid size" }, { status: 400 });
    }

    const enhance = body.enhance !== false;
    const result = await generateImage({ prompt, size, enhance });

    return NextResponse.json({
      prompt: result.prompt,
      enhancedPrompt: result.enhancedPrompt,
      width: result.width,
      height: result.height,
      mimeType: result.mimeType,
      dataUrl: result.dataUrl,
    });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
