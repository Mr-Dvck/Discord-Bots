"""Moderation logs / notes / warnings from mod.csv."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import DANGER_COLOR, admin_check, embed


class ModlogCog(commands.GroupCog, group_name="modlog"):
    """Cases, warnings, notes (Administrator only)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
        self.interaction_check = self._admin_only  # type: ignore[method-assign]

    async def _admin_only(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise discord.app_commands.CheckFailure("Server only.")
        if not interaction.user.guild_permissions.administrator:
            raise discord.app_commands.CheckFailure("Administrator only.")
        return True

    @app_commands.command(name="modlogs", description="Get a list of moderation logs for a user")
    @admin_check()
    async def modlogs(self, interaction: discord.Interaction, user: discord.Member | discord.User):
        rows = await self.bot.db.get_cases_for_user(interaction.guild.id, user.id)
        if not rows:
            await interaction.response.send_message(embed=embed("📋 Modlogs", f"No cases for {user}."))
            return
        lines = [
            f"• `#{r['id']}` **{r['action']}** — {r['reason'] or '—'} · {r['created_at'][:16]}"
            for r in rows
        ]
        await interaction.response.send_message(embed=embed(f"📋 Modlogs · {user}", "\n".join(lines)[:4000]))

    @app_commands.command(name="case", description="Show a single mod log case")
    @admin_check()
    async def case(self, interaction: discord.Interaction, case_id: int):
        row = await self.bot.db.get_case(interaction.guild.id, case_id)
        if not row:
            await interaction.response.send_message("Case not found.", ephemeral=True)
            return
        e = embed(f"Case #{row['id']} · {row['action']}")
        e.add_field(name="User", value=str(row["user_id"]), inline=True)
        e.add_field(name="Mod", value=str(row["mod_id"]), inline=True)
        e.add_field(name="Active", value=str(bool(row["active"])), inline=True)
        e.add_field(name="Duration", value=row["duration"] or "—", inline=True)
        e.add_field(name="Reason", value=row["reason"] or "—", inline=False)
        e.add_field(name="Created", value=row["created_at"] or "—", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="reason", description="Supply a reason for a mod log case")
    @admin_check()
    async def reason(self, interaction: discord.Interaction, case_id: int, reason: str):
        ok = await self.bot.db.set_case_reason(interaction.guild.id, case_id, reason)
        if not ok:
            await interaction.response.send_message("Case not found.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed("✏️ Reason", f"Case `#{case_id}` reason updated."))

    @app_commands.command(name="warnings", description="Get warnings for a user")
    @admin_check()
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        rows = await self.bot.db.get_warnings(interaction.guild.id, user.id)
        if not rows:
            await interaction.response.send_message(embed=embed("⚠️ Warnings", f"No warnings for {user.mention}."))
            return
        lines = [
            f"• `#{r['id']}` by <@{r['mod_id']}> — {r['reason']} ({r['created_at'][:16]})"
            for r in rows
        ]
        await interaction.response.send_message(
            embed=embed(f"⚠️ Warnings · {user}", "\n".join(lines), DANGER_COLOR)
        )

    @app_commands.command(name="delwarn", description="Delete a warning")
    @admin_check()
    async def delwarn(self, interaction: discord.Interaction, warn_id: int):
        ok = await self.bot.db.delete_warning(interaction.guild.id, warn_id)
        if not ok:
            await interaction.response.send_message("Warning not found.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed("🗑️ Warning", f"Deleted warning `#{warn_id}`."))

    @app_commands.command(name="note", description="Add note(s) about a member")
    @admin_check()
    async def note(self, interaction: discord.Interaction, user: discord.Member, content: str):
        nid = await self.bot.db.add_member_note(
            interaction.guild.id, user.id, interaction.user.id, content
        )
        await interaction.response.send_message(
            embed=embed("📝 Note", f"Note `#{nid}` added for {user.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="notes", description="Get notes for a user")
    @admin_check()
    async def notes(self, interaction: discord.Interaction, user: discord.Member):
        rows = await self.bot.db.get_member_notes(interaction.guild.id, user.id)
        if not rows:
            await interaction.response.send_message(
                embed=embed("📝 Notes", f"No notes for {user.mention}."), ephemeral=True
            )
            return
        lines = [
            f"• `#{r['id']}` by <@{r['mod_id']}> — {r['content'][:120]} ({r['created_at'][:16]})"
            for r in rows
        ]
        await interaction.response.send_message(
            embed=embed(f"📝 Notes · {user}", "\n".join(lines)), ephemeral=True
        )

    @app_commands.command(name="delnote", description="Delete a note about a member")
    @admin_check()
    async def delnote(self, interaction: discord.Interaction, note_id: int):
        ok = await self.bot.db.delete_member_note(interaction.guild.id, note_id)
        if not ok:
            await interaction.response.send_message("Note not found.", ephemeral=True)
            return
        await interaction.response.send_message(embed=embed("🗑️ Note", f"Deleted note `#{note_id}`."), ephemeral=True)

    @app_commands.command(name="clearnotes", description="Delete all notes for a member")
    @admin_check()
    async def clearnotes(self, interaction: discord.Interaction, user: discord.Member):
        n = await self.bot.db.clear_member_notes(interaction.guild.id, user.id)
        await interaction.response.send_message(
            embed=embed("🧹 Notes", f"Cleared **{n}** note(s) for {user.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="editnote", description="Edit a note about a member")
    @admin_check()
    async def editnote(self, interaction: discord.Interaction, note_id: int, content: str):
        ok = await self.bot.db.edit_member_note(interaction.guild.id, note_id, content)
        if not ok:
            await interaction.response.send_message("Note not found.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=embed("✏️ Note", f"Updated note `#{note_id}`."), ephemeral=True
        )

    @app_commands.command(name="modstats", description="Get moderation statistics for a mod/admin")
    @admin_check()
    async def modstats(self, interaction: discord.Interaction, mod: discord.Member | None = None):
        mod = mod or interaction.user
        stats = await self.bot.db.mod_stats(interaction.guild.id, mod.id)
        if not stats:
            await interaction.response.send_message(embed=embed("📊 Mod Stats", f"No cases by {mod.mention}."))
            return
        lines = [f"• **{k}**: {v}" for k, v in sorted(stats.items(), key=lambda x: -x[1])]
        await interaction.response.send_message(
            embed=embed(f"📊 Mod Stats · {mod}", "\n".join(lines))
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ModlogCog(bot))
