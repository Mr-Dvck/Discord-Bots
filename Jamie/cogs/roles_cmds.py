"""Roles slash commands from roles.csv."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import admin_check, embed


class RanksCog(commands.GroupCog, group_name="ranks"):
    """Joinable ranks and role info."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="addrank", description="Add a new rank for members to join (role must exist)")
    @admin_check()
    async def addrank(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.add_rank(interaction.guild.id, role.id)
        await interaction.response.send_message(
            embed=embed("🎭 Rank Added", f"{role.mention} is now a joinable rank.")
        )

    @app_commands.command(name="delrank", description="Delete an existing rank (does not delete the role)")
    @admin_check()
    async def delrank(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.del_rank(interaction.guild.id, role.id)
        await interaction.response.send_message(
            embed=embed("🎭 Rank Removed", f"{role.mention} is no longer a joinable rank.")
        )

    @app_commands.command(name="rank", description="Join/leave a rank")
    async def rank(self, interaction: discord.Interaction, role: discord.Role):
        rank_ids = await self.bot.db.list_ranks(interaction.guild.id)
        if role.id not in rank_ids:
            await interaction.response.send_message(
                "That role is not a joinable rank. Ask an admin to `/ranks addrank`.",
                ephemeral=True,
            )
            return
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Server only.", ephemeral=True)
            return
        if role in member.roles:
            await member.remove_roles(role, reason="Left rank")
            await interaction.response.send_message(embed=embed("➖ Rank", f"Left {role.mention}."))
        else:
            await member.add_roles(role, reason="Joined rank")
            await interaction.response.send_message(embed=embed("➕ Rank", f"Joined {role.mention}."))

    @app_commands.command(name="list", description="Get a list of joinable ranks")
    async def ranks_list(self, interaction: discord.Interaction):
        rank_ids = await self.bot.db.list_ranks(interaction.guild.id)
        roles = [interaction.guild.get_role(r) for r in rank_ids]
        roles = [r for r in roles if r]
        if not roles:
            await interaction.response.send_message(embed=embed("🎭 Ranks", "No joinable ranks yet."))
            return
        lines = [f"• {r.mention} — {len(r.members)} members" for r in roles]
        await interaction.response.send_message(embed=embed("🎭 Joinable Ranks", "\n".join(lines)))

    @app_commands.command(name="roles", description="Get a list of server roles")
    async def roles(self, interaction: discord.Interaction):
        roles = [r for r in interaction.guild.roles if not r.is_default()]
        roles = list(reversed(roles))
        lines = [f"• {r.mention} (`{r.id}`) — {len(r.members)}" for r in roles[:40]]
        more = f"\n…and {len(roles) - 40} more" if len(roles) > 40 else ""
        await interaction.response.send_message(
            embed=embed(f"📜 Roles ({len(roles)})", "\n".join(lines) + more)
        )

    @app_commands.command(name="roleinfo", description="Get information about a role")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        e = embed(f"ℹ️ {role.name}")
        e.color = role.color if role.color.value else 0x39B7C4
        e.add_field(name="ID", value=str(role.id), inline=True)
        e.add_field(name="Members", value=str(len(role.members)), inline=True)
        e.add_field(name="Position", value=str(role.position), inline=True)
        e.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        e.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
        e.add_field(name="Color", value=str(role.color), inline=True)
        e.add_field(name="Created", value=discord.utils.format_dt(role.created_at, "R"), inline=False)
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(RanksCog(bot))
