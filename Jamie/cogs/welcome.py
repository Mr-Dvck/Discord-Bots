"""
Welcome module (listener only — no slash commands).

Config lives in the dashboard Modules tab (channel, message, image line, DM).
On member join → different colored code block of welcome text.
"""

from __future__ import annotations

import logging
import random

import discord
from discord.ext import commands

log = logging.getLogger("jamie.welcome")


def _format_message(template: str, member: discord.Member) -> str:
    guild = member.guild
    count = guild.member_count or len(guild.members)
    # Replace mentions with display name/username for the code block (since mentions don't format inside code blocks)
    repl = {
        "{user}": member.display_name,
        "{username}": member.name,
        "{displayname}": member.display_name,
        "{server}": guild.name,
        "{membercount}": str(count),
        "{mention}": member.display_name,
    }
    out = template or ""
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


class WelcomeCog(commands.Cog):
    """Automatic join welcome code blocks. Configure via dashboard Modules — not slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot or not member.guild:
            return
        db = getattr(self.bot, "db", None)
        if not db:
            return

        cfg = await db.get_welcome_config(member.guild.id)
        if not cfg.get("enabled") or not cfg.get("channel_id"):
            return

        channel = member.guild.get_channel(cfg["channel_id"])
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(cfg["channel_id"])
            except (discord.HTTPException, discord.NotFound):
                log.warning(
                    "Welcome channel %s missing for guild %s",
                    cfg["channel_id"],
                    member.guild.id,
                )
                return

        if not isinstance(channel, discord.TextChannel):
            return
        me = member.guild.me
        if me and not channel.permissions_for(me).send_messages:
            return

        try:
            await self._send_welcome(member, channel, cfg)
        except Exception:
            log.exception(
                "Welcome failed for %s in guild %s",
                member.id,
                member.guild.id,
            )

    async def _send_welcome(
        self,
        member: discord.Member,
        channel: discord.TextChannel,
        cfg: dict,
    ):
        raw_message = cfg.get("message") or "Welcome {user} — you are now Certified."
        text = _format_message(raw_message, member)

        # List of high-contrast, premium ANSI colors using Unicode escape format
        ansi_colors = [
            "\u001b[1;31m",  # Bold Red
            "\u001b[1;32m",  # Bold Green
            "\u001b[1;33m",  # Bold Yellow
            "\u001b[1;34m",  # Bold Blue
            "\u001b[1;35m",  # Bold Pink/Magenta
            "\u001b[1;36m",  # Bold Cyan
            "\u001b[1;37m",  # Bold White
        ]
        color = random.choice(ansi_colors)
        reset = "\u001b[0m"

        # Construct different colored code block of welcome text
        code_block = f"```ansi\n{color}{text}{reset}\n```"

        # Ping the member outside of the code block so they are notified,
        # followed by the colored welcome text.
        ping_content = f"{member.mention}"
        final_message = f"{ping_content}\n{code_block}"

        await channel.send(content=final_message)

        if cfg.get("dm_on_join"):
            try:
                # For DM, we also send the code block message
                dm_content = f"Welcome to **{member.guild.name}**!\n{code_block}"
                await member.send(content=dm_content)
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
