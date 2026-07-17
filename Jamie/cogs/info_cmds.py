"""Info slash commands from info.csv: info, stats, uptime, ping, premium."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import JAMIE_COLOR, embed


class InfoCog(commands.GroupCog, group_name="bot"):
    """Bot info pack (info.csv)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="info", description="Get bot info")
    async def info(self, interaction: discord.Interaction):
        bot_user = self.bot.user
        e = embed(
            "🔥 Jamie",
            "Sentient Discord bot — memory, cartography, moderation, and chaos.",
        )
        if bot_user:
            e.set_thumbnail(url=bot_user.display_avatar.url)
            e.add_field(name="ID", value=str(bot_user.id), inline=True)
        e.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        e.add_field(
            name="Users",
            value=str(sum(g.member_count or 0 for g in self.bot.guilds)),
            inline=True,
        )
        e.add_field(name="Library", value=f"discord.py {discord.__version__}", inline=True)
        e.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="stats", description="Get bot stats")
    async def stats_cmd(self, interaction: discord.Interaction):
        started = getattr(self.bot, "started_at", None)
        uptime = "unknown"
        if started:
            delta = datetime.now(timezone.utc) - started
            uptime = str(delta).split(".")[0]
        e = embed("📊 Bot Stats")
        e.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        e.add_field(name="Commands", value=str(len(list(self.bot.tree.walk_commands()))), inline=True)
        e.add_field(name="Uptime", value=uptime, inline=True)
        e.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="uptime", description="Get bot uptime")
    async def uptime(self, interaction: discord.Interaction):
        started = getattr(self.bot, "started_at", None)
        if not started:
            await interaction.response.send_message("Uptime unavailable yet.")
            return
        delta = datetime.now(timezone.utc) - started
        await interaction.response.send_message(
            embed=embed("⏱️ Uptime", f"Online for **{str(delta).split('.')[0]}**")
        )

    @app_commands.command(name="ping", description="Ping the bot")
    async def ping(self, interaction: discord.Interaction):
        t0 = time.perf_counter()
        await interaction.response.defer(thinking=False)
        roundtrip = (time.perf_counter() - t0) * 1000
        await interaction.followup.send(
            embed=embed(
                "🏓 Pong",
                f"WebSocket: **{round(self.bot.latency * 1000)}ms**\n"
                f"Round-trip: **{round(roundtrip)}ms**",
            )
        )

    @app_commands.command(
        name="premium",
        description="Dyno premium information (responds in DM)",
    )
    async def premium(self, interaction: discord.Interaction):
        text = (
            "**Jamie Premium** (inspired by Dyno Premium)\n\n"
            "Jamie is free to run on your servers. Premium-style features "
            "(extra modules, higher limits, priority) can be layered on later.\n\n"
            "For now everything in this bot is available without a paywall."
        )
        try:
            await interaction.user.send(embed=embed("⭐ Premium", text))
            await interaction.response.send_message(
                "Sent premium info to your DMs.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=embed("⭐ Premium", text), ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))
