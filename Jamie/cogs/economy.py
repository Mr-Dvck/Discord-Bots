"""Economy slash commands from Command-Description.csv: daily, work, pay."""

from __future__ import annotations

import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import OK_COLOR, embed


class EconomyCog(commands.GroupCog, group_name="economy"):
    """Claims, work, and coin transfers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="daily", description="Claims your daily reward")
    async def daily(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        db = self.bot.db
        eco = await db.get_economy(interaction.user.id, interaction.guild.id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if eco.get("last_daily") == today:
            await interaction.response.send_message(
                "You already claimed today's reward. Come back tomorrow.",
                ephemeral=True,
            )
            return
        amount = random.randint(80, 150)
        total = await db.add_coins(interaction.user.id, interaction.guild.id, amount)
        await db.set_daily(interaction.user.id, interaction.guild.id, today)
        await interaction.response.send_message(
            embed=embed(
                "💰 Daily Reward",
                f"You claimed **{amount}** coins.\nBalance: **{total}** coins.",
                OK_COLOR,
            )
        )

    @app_commands.command(name="work", description="Work to earn coins (up to 10x/day)")
    async def work(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        db = self.bot.db
        eco = await db.get_economy(interaction.user.id, interaction.guild.id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = eco.get("work_count") or 0
        if eco.get("work_date") != today:
            count = 0
        if count >= 10:
            await interaction.response.send_message(
                "You've worked 10 times today. Rest up.",
                ephemeral=True,
            )
            return
        amount = random.randint(15, 45)
        jobs = ["ran the registers", "stacked crates", "modded a server", "scrubbed logs", "wrote riffs"]
        total = await db.add_coins(interaction.user.id, interaction.guild.id, amount)
        await db.set_work(interaction.user.id, interaction.guild.id, today, count + 1)
        await interaction.response.send_message(
            embed=embed(
                "🛠️ Work",
                f"You {random.choice(jobs)} and earned **{amount}** coins "
                f"({count + 1}/10 today).\nBalance: **{total}**.",
                OK_COLOR,
            )
        )

    @app_commands.command(name="pay", description="Transfer coins to another user")
    @app_commands.describe(user="Who to pay", amount="How many coins")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: app_commands.Range[int, 1, 1_000_000]):
        if not interaction.guild:
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        if user.bot or user.id == interaction.user.id:
            await interaction.response.send_message("Can't pay that target.", ephemeral=True)
            return
        db = self.bot.db
        eco = await db.get_economy(interaction.user.id, interaction.guild.id)
        if (eco.get("coins") or 0) < amount:
            await interaction.response.send_message(
                f"You only have **{eco.get('coins') or 0}** coins.",
                ephemeral=True,
            )
            return
        await db.add_coins(interaction.user.id, interaction.guild.id, -amount)
        receiver = await db.add_coins(user.id, interaction.guild.id, amount)
        await interaction.response.send_message(
            embed=embed(
                "💸 Payment",
                f"Sent **{amount}** coins to {user.mention}.\nThey now have **{receiver}**.",
                OK_COLOR,
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
