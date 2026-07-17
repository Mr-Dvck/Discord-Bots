"""Misc slash commands from misc.csv."""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import JAMIE_COLOR, embed, parse_duration, parse_hex_color


class MiscCog(commands.GroupCog, group_name="misc"):
    """Utility / fun commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="afk", description="Set an AFK status to display when mentioned")
    async def afk(self, interaction: discord.Interaction, message: str = "AFK"):
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        await self.bot.db.set_afk(interaction.user.id, interaction.guild.id, message)
        await interaction.response.send_message(
            embed=embed("💤 AFK", f"Set AFK: **{message}**")
        )

    @app_commands.command(name="avatar", description="Get a user's avatar")
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None):
        user = user or interaction.user
        e = embed(f"Avatar · {user}")
        e.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="randomcolor", description="Generate a random hex color with preview")
    async def randomcolor(self, interaction: discord.Interaction):
        value = random.randint(0, 0xFFFFFF)
        hex_str = f"{value:06X}"
        e = embed("🎨 Random Color", f"`#{hex_str}`")
        e.color = value
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="discrim", description="Show users with a certain discriminator")
    async def discrim(self, interaction: discord.Interaction, discriminator: str = "0"):
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        # Modern Discord: discriminator often "0"; match by legacy or last 4 of name if numeric
        matches = [
            m
            for m in interaction.guild.members
            if m.discriminator == discriminator or str(m.discriminator) == discriminator
        ][:30]
        if not matches:
            await interaction.response.send_message(
                embed=embed("Discriminators", f"No members with discrim `{discriminator}`.")
            )
            return
        lines = [f"• {m} (`{m.id}`)" for m in matches]
        await interaction.response.send_message(
            embed=embed(f"Discrim #{discriminator}", "\n".join(lines))
        )

    @app_commands.command(name="membercount", description="Get the server member count")
    async def membercount(self, interaction: discord.Interaction):
        g = interaction.guild
        humans = sum(1 for m in g.members if not m.bot)
        bots = sum(1 for m in g.members if m.bot)
        await interaction.response.send_message(
            embed=embed(
                "👥 Member Count",
                f"**Total:** {g.member_count}\n**Humans:** {humans}\n**Bots:** {bots}",
            )
        )

    @app_commands.command(name="remindme", description="Set a reminder")
    @app_commands.describe(when="e.g. 10m, 2h, 1d", message="What to remind you about")
    async def remindme(self, interaction: discord.Interaction, when: str, message: str):
        delta = parse_duration(when)
        if not delta:
            await interaction.response.send_message("Invalid time. Use 10m, 2h, 1d.", ephemeral=True)
            return
        when_dt = datetime.now(timezone.utc) + delta
        rid = await self.bot.db.add_reminder(
            interaction.user.id,
            interaction.guild.id if interaction.guild else 0,
            interaction.channel.id,
            message,
            when_dt.isoformat(),
        )
        await interaction.response.send_message(
            embed=embed(
                "⏰ Reminder",
                f"I'll remind you <t:{int(when_dt.timestamp())}:R>\n`#{rid}`: {message}",
            )
        )

    @app_commands.command(name="whois", description="Get user information")
    async def whois(self, interaction: discord.Interaction, user: discord.Member | None = None):
        user = user or interaction.user
        e = embed(f"Whois · {user}")
        e.set_thumbnail(url=user.display_avatar.url)
        e.add_field(name="ID", value=str(user.id), inline=True)
        e.add_field(name="Bot", value=str(user.bot), inline=True)
        e.add_field(name="Created", value=discord.utils.format_dt(user.created_at, "R"), inline=False)
        if isinstance(user, discord.Member):
            e.add_field(
                name="Joined",
                value=discord.utils.format_dt(user.joined_at, "R") if user.joined_at else "—",
                inline=False,
            )
            roles = [r.mention for r in user.roles if not r.is_default()]
            e.add_field(name="Roles", value=", ".join(roles[:15]) or "None", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="inviteinfo", description="Get information about an invite")
    async def inviteinfo(self, interaction: discord.Interaction, code: str):
        code = code.rstrip("/").split("/")[-1]
        try:
            inv = await self.bot.fetch_invite(code, with_counts=True)
        except discord.NotFound:
            await interaction.response.send_message("Invite not found.", ephemeral=True)
            return
        e = embed(f"Invite · {inv.code}")
        e.add_field(name="Server", value=inv.guild.name if inv.guild else "Unknown", inline=True)
        e.add_field(name="Channel", value=str(inv.channel) if inv.channel else "—", inline=True)
        e.add_field(name="Uses", value=str(inv.approximate_member_count or inv.uses or "—"), inline=True)
        e.add_field(name="Online", value=str(getattr(inv, "approximate_presence_count", "—")), inline=True)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="roll", description="Roll the dice")
    @app_commands.describe(dice="e.g. 1d6, 2d20")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        dice = dice.lower().replace(" ", "")
        try:
            if "d" not in dice:
                raise ValueError
            n, sides = dice.split("d", 1)
            n = int(n or "1")
            sides = int(sides)
            if n < 1 or n > 50 or sides < 2 or sides > 1000:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Use NdS like `2d6`.", ephemeral=True)
            return
        rolls = [random.randint(1, sides) for _ in range(n)]
        await interaction.response.send_message(
            embed=embed("🎲 Roll", f"`{dice}` → {rolls} = **{sum(rolls)}**")
        )

    @app_commands.command(name="flipcoin", description="Flip a coin")
    async def flipcoin(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=embed("🪙 Coin Flip", f"**{random.choice(['Heads', 'Tails'])}**")
        )

    @app_commands.command(name="serverinfo", description="Get server info/stats")
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        e = embed(g.name)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="ID", value=str(g.id), inline=True)
        e.add_field(name="Owner", value=str(g.owner), inline=True)
        e.add_field(name="Members", value=str(g.member_count), inline=True)
        e.add_field(name="Channels", value=str(len(g.channels)), inline=True)
        e.add_field(name="Roles", value=str(len(g.roles)), inline=True)
        e.add_field(name="Boosts", value=str(g.premium_subscription_count or 0), inline=True)
        e.add_field(name="Created", value=discord.utils.format_dt(g.created_at, "R"), inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="dynoavatar", description="Generate a Dyno-like avatar")
    async def dynoavatar(self, interaction: discord.Interaction, user: discord.User | None = None):
        user = user or interaction.user
        e = embed("Dyno-style Avatar", f"Preview for {user.mention}")
        e.color = JAMIE_COLOR
        e.set_image(url=user.display_avatar.replace(size=256).url)
        e.set_footer(text="Jamie · teal frame vibe")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="distance", description="Get distance between two coordinate sets")
    @app_commands.describe(
        lat1="Latitude 1", lon1="Longitude 1", lat2="Latitude 2", lon2="Longitude 2"
    )
    async def distance(
        self,
        interaction: discord.Interaction,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ):
        # Haversine km
        r = 6371.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        km = r * c
        await interaction.response.send_message(
            embed=embed("📏 Distance", f"**{km:.2f} km** ({km * 0.621371:.2f} mi)")
        )

    @app_commands.command(name="color", description="Show a color using hex")
    async def color(self, interaction: discord.Interaction, hex_color: str):
        value = parse_hex_color(hex_color)
        if value is None:
            await interaction.response.send_message("Invalid hex. Use `#RRGGBB`.", ephemeral=True)
            return
        e = embed("🎨 Color", f"`#{value:06X}`")
        e.color = value
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="emotes", description="Get a list of server emojis")
    async def emotes(self, interaction: discord.Interaction):
        emojis = list(interaction.guild.emojis)
        if not emojis:
            await interaction.response.send_message(embed=embed("Emotes", "No custom emojis."))
            return
        lines = [f"{e} `:{e.name}:`" for e in emojis[:50]]
        more = f"\n…+{len(emojis) - 50} more" if len(emojis) > 50 else ""
        await interaction.response.send_message(
            embed=embed(f"Emotes ({len(emojis)})", " ".join(lines) + more)
        )

    @app_commands.command(name="covid", description="Get COVID-19 stats")
    async def covid(self, interaction: discord.Interaction, country: str = "global"):
        await interaction.response.send_message(
            embed=embed(
                "🦠 COVID-19",
                f"Live stats APIs change frequently. For **{country}**, check "
                f"[Our World in Data](https://ourworldindata.org/coronavirus) or WHO dashboards.\n\n"
                "Jamie won't invent case numbers.",
            )
        )

    @app_commands.command(name="highlights", description="Get notified when a specific phrase is said")
    @app_commands.describe(
        action="add / remove / list",
        phrase="Phrase to watch for",
    )
    async def highlights(
        self,
        interaction: discord.Interaction,
        action: str,
        phrase: str | None = None,
    ):
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        action = action.lower()
        if action == "list":
            items = await self.bot.db.list_highlights(interaction.user.id, interaction.guild.id)
            await interaction.response.send_message(
                embed=embed("🔦 Highlights", "\n".join(f"• {p}" for p in items) or "None set."),
                ephemeral=True,
            )
            return
        if not phrase:
            await interaction.response.send_message("Provide a phrase.", ephemeral=True)
            return
        if action == "add":
            await self.bot.db.add_highlight(interaction.user.id, interaction.guild.id, phrase)
            await interaction.response.send_message(
                embed=embed("🔦 Highlight", f"Watching for `{phrase}`."), ephemeral=True
            )
        elif action == "remove":
            await self.bot.db.remove_highlight(interaction.user.id, interaction.guild.id, phrase)
            await interaction.response.send_message(
                embed=embed("🔦 Highlight", f"Removed `{phrase}`."), ephemeral=True
            )
        else:
            await interaction.response.send_message("Action must be add, remove, or list.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCog(bot))
