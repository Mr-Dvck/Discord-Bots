"""Display helpers — bold unicode channel names + Jamie chat embeds."""

from __future__ import annotations

import discord

JAMIE_COLOR = 0x39B7C4


# Not a cog — kept under cogs/ for imports; setup is a no-op so main.py load_extension is happy.
async def setup(bot):
    return


def to_bold_unicode(text: str) -> str:
    """
    Convert A-Z / a-z / 0-9 to Mathematical Sans-Serif Bold (modern bold unicode).
    Leaves hyphens, spaces, and other punctuation as-is.
    Already-bold characters pass through unchanged.
    """
    out: list[str] = []
    for ch in text:
        o = ord(ch)
        if 0x41 <= o <= 0x5A:  # A-Z
            out.append(chr(0x1D5D4 + (o - 0x41)))
        elif 0x61 <= o <= 0x7A:  # a-z
            out.append(chr(0x1D5EE + (o - 0x61)))
        elif 0x30 <= o <= 0x39:  # 0-9
            out.append(chr(0x1D7EC + (o - 0x30)))
        else:
            out.append(ch)
    return "".join(out)


def title_case_words(text: str) -> str:
    """Capitalize first letter of the title and after spaces/hyphens (Main, Bot-Kontrol)."""
    chars = list(text)
    cap_next = True
    for i, ch in enumerate(chars):
        if cap_next and ch.isalpha():
            chars[i] = ch.upper()
            cap_next = False
        elif ch in (" ", "-", "_"):
            cap_next = True
        elif ch.isalnum():
            chars[i] = ch.lower()
            cap_next = False
    return "".join(chars)


def channel_display_name(name: str, *, is_category: bool = False) -> str:
    """Title-case then Modern Bold Unicode for Discord channel/category creation."""
    raw = (name or "").strip()
    if not raw:
        return to_bold_unicode("Channel")
    # Categories may keep spaces; text channels prefer hyphens
    if not is_category:
        raw = raw.replace(" ", "-")
    # Avoid double-bolding if already mathematical bold
    if any(0x1D400 <= ord(c) <= 0x1D7FF for c in raw):
        return raw[:100]
    titled = title_case_words(raw)
    return to_bold_unicode(titled)[:100]


def split_for_embed(text: str, limit: int = 4000) -> list[str]:
    """Split long text into embed-description-sized chunks."""
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        split_at = remaining[:limit].rfind("\n\n")
        if split_at < limit // 4:
            split_at = remaining[:limit].rfind("\n")
        if split_at < limit // 4:
            split_at = remaining[:limit].rfind(". ")
            if split_at > limit // 4:
                split_at += 1
        if split_at < limit // 4:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return chunks


def jamie_embed(
    description: str,
    *,
    title: str | None = "Jamie",
    color: int = JAMIE_COLOR,
    footer: str | None = None,
) -> discord.Embed:
    e = discord.Embed(
        title=title,
        description=description[:4096] if description else None,
        color=color,
    )
    if footer:
        e.set_footer(text=footer[:2048])
    return e


async def send_jamie_embeds(
    destination: discord.abc.Messageable,
    text: str,
    *,
    title: str | None = "🔥 Jamie",
    reply_to: discord.Message | None = None,
    footer: str | None = None,
) -> list[discord.Message]:
    """Send Jamie's reply as one or more embeds (description max 4096 each)."""
    chunks = split_for_embed(text, 3900)
    sent: list[discord.Message] = []
    for i, chunk in enumerate(chunks):
        embed = jamie_embed(
            chunk,
            title=title if i == 0 else None,
            footer=footer if i == len(chunks) - 1 else (f"({i + 1}/{len(chunks)})" if len(chunks) > 1 else footer),
        )
        if i == 0 and reply_to is not None:
            msg = await reply_to.reply(embed=embed, mention_author=False)
        else:
            msg = await destination.send(embed=embed)
        sent.append(msg)
    return sent
