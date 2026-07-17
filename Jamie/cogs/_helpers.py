"""Shared helpers for slash command cogs."""

from __future__ import annotations

import re
from datetime import timedelta

import discord
from discord import app_commands

JAMIE_COLOR = 0x39B7C4
DANGER_COLOR = 0xF04747
OK_COLOR = 0x7DD3A7


def embed(title: str, description: str = "", color: int = JAMIE_COLOR) -> discord.Embed:
    return discord.Embed(title=title, description=description or None, color=color)


def parse_duration(text: str | None) -> timedelta | None:
    """Parse 10m, 1h, 2d, 1w style durations."""
    if not text:
        return None
    text = text.strip().lower()
    m = re.fullmatch(r"(\d+)\s*([smhdw])", text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[unit]
    return timedelta(seconds=n * mult)


def parse_hex_color(value: str) -> int | None:
    value = value.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return None
    return int(value, 16)


async def safe_respond(interaction: discord.Interaction, content: str | None = None, **kwargs):
    if interaction.response.is_done():
        await interaction.followup.send(content=content, **kwargs)
    else:
        await interaction.response.send_message(content=content, **kwargs)


def is_mod(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return (
        perms.kick_members
        or perms.ban_members
        or perms.manage_guild
        or perms.moderate_members
        or perms.administrator
    )


def mod_check():
    """Legacy alias — mod tools are admin-only now."""
    return admin_check()


def admin_check():
    """Require Discord Administrator permission (not just Manage Server / mod perms)."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("Server only.")
        if not interaction.user.guild_permissions.administrator:
            raise app_commands.CheckFailure("Administrator only.")
        return True

    return app_commands.check(predicate)
