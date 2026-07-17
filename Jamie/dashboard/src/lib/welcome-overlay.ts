/**
 * Client-side text overlay for welcome banners.
 * AI models garble exact text — we stamp it on the canvas after generation.
 */

export type WelcomeOverlayOptions = {
  /** Full image data URL (png/jpeg) */
  dataUrl: string;
  /** Member display name */
  memberName: string;
  /** e.g. "is now Certified" */
  suffix?: string;
  width: number;
  height: number;
};

/**
 * Draw dark gradient + exact welcome line on the image.
 * Returns a new PNG data URL.
 */
export async function applyWelcomeOverlay(
  opts: WelcomeOverlayOptions
): Promise<string> {
  const suffix = opts.suffix ?? "is now Certified";
  const name = (opts.memberName || "Member").trim() || "Member";
  const line = `${name} ${suffix}`;

  const img = await loadImage(opts.dataUrl);
  const canvas = document.createElement("canvas");
  canvas.width = opts.width || img.naturalWidth || 1280;
  canvas.height = opts.height || img.naturalHeight || 720;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas not available");

  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  // Bottom gradient for readability
  const g = ctx.createLinearGradient(0, canvas.height * 0.45, 0, canvas.height);
  g.addColorStop(0, "rgba(10,14,18,0)");
  g.addColorStop(0.45, "rgba(10,14,18,0.55)");
  g.addColorStop(1, "rgba(10,14,18,0.88)");
  ctx.fillStyle = g;
  ctx.fillRect(0, canvas.height * 0.4, canvas.width, canvas.height * 0.6);

  // Fit font to width
  const maxWidth = canvas.width * 0.9;
  let fontSize = Math.floor(canvas.height * 0.09);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const fontFamily =
    '"Inter", ui-sans-serif, system-ui, -apple-system, sans-serif';

  while (fontSize > 18) {
    ctx.font = `700 ${fontSize}px ${fontFamily}`;
    if (ctx.measureText(line).width <= maxWidth) break;
    fontSize -= 2;
  }

  const x = canvas.width / 2;
  const y = canvas.height * 0.78;

  // Shadow / glow
  ctx.shadowColor = "rgba(57,183,196,0.65)";
  ctx.shadowBlur = Math.max(12, fontSize * 0.35);
  ctx.fillStyle = "#e8f0f4";
  ctx.font = `700 ${fontSize}px ${fontFamily}`;
  ctx.fillText(line, x, y);

  // Crisp stroke for legibility
  ctx.shadowBlur = 0;
  ctx.lineWidth = Math.max(2, fontSize * 0.04);
  ctx.strokeStyle = "rgba(0,0,0,0.55)";
  ctx.strokeText(line, x, y);
  ctx.fillStyle = "#f4fbfd";
  ctx.fillText(line, x, y);

  // Accent underline
  const textW = ctx.measureText(line).width;
  ctx.fillStyle = "rgba(57,183,196,0.9)";
  const barH = Math.max(3, fontSize * 0.08);
  ctx.fillRect(x - textW / 2, y + fontSize * 0.55, textW, barH);

  return canvas.toDataURL("image/png");
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to load image for overlay"));
    img.src = src;
  });
}
