"""
Welcome banners: cached/procedural background + exact text (no avatar, no AI per join).
Background art is set once from the dashboard module (or default procedural).
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger("jamie.welcome")

BANNER_W = 1280
BANNER_H = 720

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "welcome_bgs"

DEFAULT_BG_PROMPT = (
    "Dark cyberpunk Discord welcome banner background for a server called Certified, "
    "neon cyan and lime accents, gritty metal and night energy, cinematic wide composition, "
    "empty lower third for text overlay, high detail, NO text, NO letters, NO watermarks"
)


def guild_bg_path(guild_id: int | str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"{guild_id}.png"


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def make_default_background(width: int = BANNER_W, height: int = BANNER_H) -> Image.Image:
    """Fast procedural Certified-style dark cyan background (no network)."""
    img = Image.new("RGB", (width, height), (10, 14, 18))
    draw = ImageDraw.Draw(img, "RGBA")

    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(10 + 8 * t)
        g = int(14 + 20 * t)
        b = int(18 + 28 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse(
        [-width * 0.15, -height * 0.2, width * 0.55, height * 0.7],
        fill=(57, 183, 196, 45),
    )
    od.ellipse(
        [width * 0.45, height * 0.2, width * 1.15, height * 1.1],
        fill=(125, 211, 167, 28),
    )
    od.rectangle([0, int(height * 0.55), width, height], fill=(0, 0, 0, 110))
    od.rectangle([0, 0, 10, height], fill=(57, 183, 196, 180))
    od.rectangle([width - 10, 0, width, height], fill=(57, 183, 196, 100))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img.filter(ImageFilter.GaussianBlur(radius=0.6))


def load_background(path: str | Path | None = None) -> Image.Image:
    if path:
        p = Path(path)
        if p.is_file():
            try:
                im = Image.open(p).convert("RGB")
                if im.size != (BANNER_W, BANNER_H):
                    im = im.resize((BANNER_W, BANNER_H), Image.Resampling.LANCZOS)
                return im
            except Exception as e:
                log.warning("Failed to load welcome bg %s: %s", p, e)
    return make_default_background()


def render_welcome_banner(
    *,
    member_name: str,
    image_line: str = "is now Certified",
    background_path: str | Path | None = None,
    subtitle: str | None = None,
) -> bytes:
    """
    Composite welcome PNG bytes.
    Line: "{member_name} {image_line}" e.g. "Duck is now Certified"
    No avatar — just the banner art + exact text.
    """
    name = (member_name or "Member").strip() or "Member"
    suffix = (image_line or "is now Certified").strip() or "is now Certified"
    line = f"{name} {suffix}"

    base = load_background(background_path).convert("RGBA")
    w, h = base.size

    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(int(h * 0.4), h):
        t = (y - h * 0.4) / (h * 0.6)
        alpha = int(50 + 180 * min(1.0, max(0.0, t)))
        gd.line([(0, y), (w, y)], fill=(8, 12, 16, alpha))
    base = Image.alpha_composite(base, grad)
    draw = ImageDraw.Draw(base)

    max_width = int(w * 0.9)
    font_size = 72
    font = _load_font(font_size)
    while font_size > 22:
        font = _load_font(font_size)
        bbox = draw.textbbox((0, 0), line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            break
        font_size -= 2

    text_y = int(h * 0.58)
    shadow = (0, 0, 0, 160)
    for dx, dy in ((3, 3), (1, 2), (-1, 1)):
        draw.text(
            (w // 2 + dx, text_y + dy),
            line,
            font=font,
            fill=shadow,
            anchor="mm",
        )
    draw.text(
        (w // 2, text_y),
        line,
        font=font,
        fill=(244, 251, 253, 255),
        anchor="mm",
    )

    bbox = draw.textbbox((w // 2, text_y), line, font=font, anchor="mm")
    bar_y = bbox[3] + 14
    bar_pad = 10
    draw.rounded_rectangle(
        [bbox[0] - bar_pad, bar_y, bbox[2] + bar_pad, bar_y + 6],
        radius=3,
        fill=(57, 183, 196, 230),
    )

    if subtitle:
        sub_font = _load_font(max(18, font_size // 3))
        draw.text(
            (w // 2, bar_y + 32),
            subtitle,
            font=sub_font,
            fill=(180, 200, 210, 220),
            anchor="mm",
        )

    out = base.convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def ensure_guild_background(
    image_gen,
    guild_id: int | str,
    *,
    force: bool = False,
    prompt: str | None = None,
) -> Path:
    """Save a background PNG for this guild (AI once, or procedural fallback)."""
    path = guild_bg_path(guild_id)
    if path.is_file() and not force:
        return path

    if image_gen is not None:
        try:
            data = await image_gen.generate(
                prompt or DEFAULT_BG_PROMPT,
                width=BANNER_W,
                height=BANNER_H,
            )
            if data:
                path.write_bytes(data)
                log.info("Saved AI welcome background for guild %s (%d bytes)", guild_id, len(data))
                return path
        except Exception as e:
            log.warning("AI welcome bg failed for %s: %s", guild_id, e)

    make_default_background().save(path, format="PNG")
    log.info("Saved procedural welcome background for guild %s", guild_id)
    return path
