/**
 * Image generation — same stack as the Discord bot (LLM enhance + Pollinations flux).
 */

const POLLINATIONS_BASE = "https://image.pollinations.ai/prompt";

export type ImageSize =
  | "square"
  | "welcome"
  | "banner"
  | "portrait"
  | "story";

export const IMAGE_SIZES: Record<
  ImageSize,
  { width: number; height: number; label: string }
> = {
  square: { width: 1024, height: 1024, label: "Square 1:1" },
  welcome: { width: 1280, height: 720, label: "Welcome 16:9" },
  banner: { width: 1500, height: 500, label: "Banner 3:1" },
  portrait: { width: 768, height: 1024, label: "Portrait 3:4" },
  story: { width: 768, height: 1344, label: "Story 9:16" },
};

export async function enhanceImagePrompt(userPrompt: string): Promise<string> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = process.env.JAMIE_LLM_MODEL || "meta-llama/llama-3.3-70b-instruct";
  const apiBase = process.env.JAMIE_LLM_API_BASE || "https://openrouter.ai/api/v1";

  if (!apiKey) return userPrompt;

  try {
    const res = await fetch(`${apiBase}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: "system",
            content:
              "You are an AI image prompt engineer. Turn the user's request into a detailed, " +
              "vivid image generation prompt. Be specific about style, lighting, composition, " +
              "colors, mood. Output ONLY the prompt text, nothing else. No quotes, no explanations.",
          },
          { role: "user", content: userPrompt },
        ],
        temperature: 0.8,
        max_tokens: 220,
      }),
      cache: "no-store",
    });
    if (!res.ok) return userPrompt;
    const data = await res.json();
    const out = data?.choices?.[0]?.message?.content?.trim();
    return out?.replace(/^["']|["']$/g, "") || userPrompt;
  } catch {
    return userPrompt;
  }
}

export async function generateImageBytes(
  prompt: string,
  width = 1024,
  height = 1024
): Promise<Buffer> {
  const encoded = encodeURIComponent(prompt);
  const url =
    `${POLLINATIONS_BASE}/${encoded}` +
    `?width=${width}&height=${height}&nologo=true&model=flux&seed=${Date.now() % 1_000_000}`;

  const res = await fetch(url, {
    method: "GET",
    cache: "no-store",
    // Pollinations can be slow
    signal: AbortSignal.timeout(120_000),
  });

  if (!res.ok) {
    const err = await res.text().catch(() => "");
    throw new Error(`Image API ${res.status}: ${err.slice(0, 200)}`);
  }

  const ab = await res.arrayBuffer();
  const buf = Buffer.from(ab);
  if (buf.length < 1000) {
    throw new Error("Image response too small — generation likely failed");
  }
  return buf;
}

export async function generateImage(options: {
  prompt: string;
  enhance?: boolean;
  size?: ImageSize;
  width?: number;
  height?: number;
}): Promise<{
  prompt: string;
  enhancedPrompt: string;
  width: number;
  height: number;
  mimeType: string;
  base64: string;
  dataUrl: string;
}> {
  const raw = options.prompt.trim();
  if (!raw) throw new Error("Prompt required");

  const sizeKey = options.size || "square";
  const dims = IMAGE_SIZES[sizeKey] || IMAGE_SIZES.square;
  const width = options.width || dims.width;
  const height = options.height || dims.height;

  const enhanced =
    options.enhance === false ? raw : await enhanceImagePrompt(raw);
  const bytes = await generateImageBytes(enhanced, width, height);
  const base64 = bytes.toString("base64");
  const mimeType = "image/png";

  return {
    prompt: raw,
    enhancedPrompt: enhanced,
    width,
    height,
    mimeType,
    base64,
    dataUrl: `data:${mimeType};base64,${base64}`,
  };
}
