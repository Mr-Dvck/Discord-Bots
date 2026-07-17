"""Manage slash commands from manage.csv."""

from __future__ import annotations

import asyncio
import io
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import (
    DANGER_COLOR,
    OK_COLOR,
    admin_check,
    embed,
    parse_hex_color,
    parse_duration,
)


class ManageCog(commands.GroupCog, group_name="manage"):
    """Server management commands (Administrator only)."""

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

    # ── mods / roles ──────────────────────────────────────────────

    @app_commands.command(name="addmod", description="Add a moderator role")
    @admin_check()
    async def addmod(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.add_mod_role(interaction.guild.id, role.id)
        await interaction.response.send_message(
            embed=embed("🛡️ Mod Role", f"Added {role.mention} as a moderator role."),
            ephemeral=True,
        )

    @app_commands.command(name="delmod", description="Remove a moderator role")
    @admin_check()
    async def delmod(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.del_mod_role(interaction.guild.id, role.id)
        await interaction.response.send_message(
            embed=embed("🛡️ Mod Role", f"Removed {role.mention} from moderator roles."),
            ephemeral=True,
        )

    @app_commands.command(name="listmods", description="List moderators")
    @admin_check()
    async def listmods(self, interaction: discord.Interaction):
        role_ids = await self.bot.db.list_mod_roles(interaction.guild.id)
        roles = [interaction.guild.get_role(r) for r in role_ids]
        roles = [r for r in roles if r]
        mods = []
        for member in interaction.guild.members:
            if member.bot:
                continue
            if member.guild_permissions.administrator or any(r in member.roles for r in roles):
                mods.append(member)
        # de-dupe preserve order
        seen = set()
        unique = []
        for m in mods:
            if m.id not in seen:
                seen.add(m.id)
                unique.append(m)
        lines = [f"• {m.mention} (`{m}`)" for m in unique[:40]]
        desc = "\n".join(lines) if lines else "No moderators configured / found."
        if role_ids:
            desc = "**Mod roles:** " + ", ".join(r.mention for r in roles) + "\n\n" + desc
        await interaction.response.send_message(embed=embed("🛡️ Moderators", desc))

    @app_commands.command(name="addrole", description="Add a new role, with optional color and hoist")
    @app_commands.describe(name="Role name", color="Hex color e.g. #39b7c4", hoist="Display separately")
    @admin_check()
    async def addrole(
        self,
        interaction: discord.Interaction,
        name: str,
        color: str | None = None,
        hoist: bool = False,
    ):
        colour = discord.Color.default()
        if color:
            c = parse_hex_color(color)
            if c is None:
                await interaction.response.send_message("Invalid hex color.", ephemeral=True)
                return
            colour = discord.Color(c)
        role = await interaction.guild.create_role(name=name, colour=colour, hoist=hoist, reason=f"By {interaction.user}")
        await interaction.response.send_message(embed=embed("✅ Role Created", f"{role.mention} created."))

    @app_commands.command(name="delrole", description="Delete a role")
    @admin_check()
    async def delrole(self, interaction: discord.Interaction, role: discord.Role):
        if role >= interaction.guild.me.top_role or role.is_default():
            await interaction.response.send_message("I can't delete that role.", ephemeral=True)
            return
        name = role.name
        await role.delete(reason=f"By {interaction.user}")
        await interaction.response.send_message(embed=embed("🗑️ Role Deleted", f"Deleted **{name}**."))

    @app_commands.command(name="rolecolor", description="Change the color of a role")
    @admin_check()
    async def rolecolor(self, interaction: discord.Interaction, role: discord.Role, color: str):
        c = parse_hex_color(color)
        if c is None:
            await interaction.response.send_message("Invalid hex color.", ephemeral=True)
            return
        await role.edit(colour=discord.Color(c), reason=f"By {interaction.user}")
        await interaction.response.send_message(embed=embed("🎨 Role Color", f"{role.mention} → `#{color.lstrip('#')}`"))

    @app_commands.command(name="rolename", description="Change the name of a role")
    @admin_check()
    async def rolename(self, interaction: discord.Interaction, role: discord.Role, name: str):
        old = role.name
        await role.edit(name=name, reason=f"By {interaction.user}")
        await interaction.response.send_message(embed=embed("✏️ Role Name", f"**{old}** → **{name}**"))

    @app_commands.command(name="mentionable", description="Toggle making a role mentionable on/off")
    @admin_check()
    async def mentionable(self, interaction: discord.Interaction, role: discord.Role):
        await role.edit(mentionable=not role.mentionable, reason=f"By {interaction.user}")
        state = "mentionable" if role.mentionable else "not mentionable"
        await interaction.response.send_message(embed=embed("🔔 Mentionable", f"{role.mention} is now **{state}**."))

    @app_commands.command(name="role", description="Add/remove a user to a role or roles")
    @app_commands.describe(user="Member", role="Role to toggle")
    @admin_check()
    async def role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        if role in user.roles:
            await user.remove_roles(role, reason=f"By {interaction.user}")
            await interaction.response.send_message(embed=embed("➖ Role", f"Removed {role.mention} from {user.mention}."))
        else:
            await user.add_roles(role, reason=f"By {interaction.user}")
            await interaction.response.send_message(embed=embed("➕ Role", f"Added {role.mention} to {user.mention}."))

    # ── nick / purge / announce ───────────────────────────────────

    @app_commands.command(name="nick", description="Change the bot nickname")
    @admin_check()
    async def nick(self, interaction: discord.Interaction, nickname: str | None = None):
        me = interaction.guild.me
        await me.edit(nick=nickname)
        await interaction.response.send_message(
            embed=embed("🤖 Nickname", f"Bot nickname set to **{nickname or me.name}**.")
        )

    @app_commands.command(name="setnick", description="Change the nickname of a user")
    @admin_check()
    async def setnick(self, interaction: discord.Interaction, user: discord.Member, nickname: str | None = None):
        await user.edit(nick=nickname, reason=f"By {interaction.user}")
        await interaction.response.send_message(
            embed=embed("✏️ Nickname", f"{user.mention} → **{nickname or user.name}**")
        )

    @app_commands.command(name="purge", description="Delete a number of messages from a channel")
    @app_commands.describe(amount="1-100 messages", user="Only delete from this user")
    @admin_check()
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
        user: discord.Member | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        def check(m: discord.Message):
            return user is None or m.author.id == user.id

        deleted = await interaction.channel.purge(limit=amount, check=check)
        await interaction.followup.send(
            embed=embed("🧹 Purge", f"Deleted **{len(deleted)}** messages.", DANGER_COLOR),
            ephemeral=True,
        )

    @app_commands.command(name="announce", description="Send an announcement using the bot")
    @app_commands.describe(channel="Target channel", message="Announcement text")
    @admin_check()
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
    ):
        e = embed("📢 Announcement", message)
        e.set_footer(text=f"From {interaction.user}")
        await channel.send(embed=e)
        await interaction.response.send_message(f"Sent to {channel.mention}.", ephemeral=True)

    # ── modules / commands / prefix ───────────────────────────────

    @app_commands.command(name="modules", description="List available modules")
    @admin_check()
    async def modules(self, interaction: discord.Interaction):
        s = await self.bot.db.get_guild_settings(interaction.guild.id)
        default = {
            "moderation": True,
            "automod": True,
            "welcome": True,
            "levels": True,
            "chat": True,
            "memory": True,
            "economy": True,
            "giveaways": False,
            "starboard": False,
            "tickets": False,
        }
        mods = {**default, **(s.get("modules") or {})}
        lines = [f"{'✅' if v else '❌'} **{k}**" for k, v in mods.items()]
        await interaction.response.send_message(embed=embed("⚙️ Modules", "\n".join(lines)))

    @app_commands.command(name="module", description="Enable/disable a module")
    @app_commands.describe(name="Module name", enabled="On/off")
    @admin_check()
    async def module(self, interaction: discord.Interaction, name: str, enabled: bool):
        await self.bot.db.set_module_enabled(interaction.guild.id, name.lower(), enabled)
        state = "enabled" if enabled else "disabled"
        await interaction.response.send_message(
            embed=embed("⚙️ Module", f"Module **{name.lower()}** {state}."),
            ephemeral=True,
        )

    @app_commands.command(name="command", description="Enable/disable a command")
    @app_commands.describe(name="Command name", enabled="On/off")
    @admin_check()
    async def command_toggle(self, interaction: discord.Interaction, name: str, enabled: bool):
        await self.bot.db.set_command_enabled(interaction.guild.id, name.lower(), enabled)
        state = "enabled" if enabled else "disabled"
        await interaction.response.send_message(
            embed=embed("⌨️ Command", f"Command **{name.lower()}** {state}."),
            ephemeral=True,
        )

    @app_commands.command(name="prefix", description="Get or set the command prefix")
    @app_commands.describe(new_prefix="Leave empty to view current prefix")
    @admin_check()
    async def prefix(self, interaction: discord.Interaction, new_prefix: str | None = None):
        if new_prefix is None:
            s = await self.bot.db.get_guild_settings(interaction.guild.id)
            await interaction.response.send_message(
                embed=embed("🔤 Prefix", f"Current prefix: `{s.get('prefix') or '?'}`")
            )
            return
        if len(new_prefix) > 5:
            await interaction.response.send_message("Prefix max 5 chars.", ephemeral=True)
            return
        await self.bot.db.set_guild_prefix(interaction.guild.id, new_prefix)
        await interaction.response.send_message(embed=embed("🔤 Prefix", f"Prefix set to `{new_prefix}`"))

    # ── ignores ───────────────────────────────────────────────────

    @app_commands.command(name="ignorechannel", description="Toggle command usage in a channel")
    @admin_check()
    async def ignorechannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        now = await self.bot.db.toggle_ignore(interaction.guild.id, "channel", channel.id)
        await interaction.response.send_message(
            embed=embed("🙈 Channel", f"{channel.mention} is now **{'ignored' if now else 'allowed'}**.")
        )

    @app_commands.command(name="ignoreuser", description="Toggle command usage for a user")
    @admin_check()
    async def ignoreuser(self, interaction: discord.Interaction, user: discord.Member):
        now = await self.bot.db.toggle_ignore(interaction.guild.id, "user", user.id)
        await interaction.response.send_message(
            embed=embed("🙈 User", f"{user.mention} is now **{'ignored' if now else 'allowed'}**.")
        )

    @app_commands.command(name="ignorerole", description="Toggle command usage for a role")
    @admin_check()
    async def ignorerole(self, interaction: discord.Interaction, role: discord.Role):
        now = await self.bot.db.toggle_ignore(interaction.guild.id, "role", role.id)
        await interaction.response.send_message(
            embed=embed("🙈 Role", f"{role.mention} is now **{'ignored' if now else 'allowed'}**.")
        )

    @app_commands.command(name="clearwarn", description="Clear warnings for a user")
    @admin_check()
    async def clearwarn(self, interaction: discord.Interaction, user: discord.Member):
        n = await self.bot.db.clear_warnings(interaction.guild.id, user.id)
        await interaction.response.send_message(
            embed=embed("🧹 Warnings", f"Cleared **{n}** warning(s) for {user.mention}.")
        )

    @app_commands.command(name="customs", description="List, enable, disable custom commands")
    @admin_check()
    async def customs(self, interaction: discord.Interaction):
        s = await self.bot.db.get_guild_settings(interaction.guild.id)
        customs = s.get("custom_cmds") or []
        if not customs:
            await interaction.response.send_message(
                embed=embed("✨ Custom Commands", "No custom commands configured yet.")
            )
            return
        lines = [f"• `{c}`" for c in customs]
        await interaction.response.send_message(embed=embed("✨ Custom Commands", "\n".join(lines)))

    @app_commands.command(name="giveaway", description="Create and manage giveaways")
    @app_commands.describe(
        prize="Prize text",
        duration="e.g. 1h, 1d",
        winners="Number of winners",
    )
    @admin_check()
    async def giveaway(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: str = "1d",
        winners: app_commands.Range[int, 1, 20] = 1,
    ):
        delta = parse_duration(duration)
        if not delta:
            await interaction.response.send_message("Invalid duration. Use 10m, 1h, 1d, 1w.", ephemeral=True)
            return
        ends = datetime.now(timezone.utc) + delta
        e = embed(
            "🎁 Giveaway",
            f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(ends.timestamp())}:R>\n\nReact with 🎉 to enter!",
            OK_COLOR,
        )
        e.set_footer(text=f"Hosted by {interaction.user}")
        await interaction.response.send_message(embed=e)
        msg = await interaction.original_response()
        await msg.add_reaction("🎉")
        # Store lightweight giveaway
        try:
            await self.bot.db._conn.execute(
                """
                INSERT INTO giveaways (guild_id, channel_id, message_id, prize, ends_at, winners)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction.guild.id,
                    interaction.channel.id,
                    msg.id,
                    prize,
                    ends.isoformat(),
                    winners,
                ),
            )
            await self.bot.db._conn.commit()
        except Exception:
            pass

    @app_commands.command(name="addemote", description="Add an emote to the server")
    @app_commands.describe(name="Emoji name", image_url="Direct image URL (png/jpg/gif)")
    @admin_check()
    async def addemote(self, interaction: discord.Interaction, name: str, image_url: str):
        await interaction.response.defer(ephemeral=True)
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Could not download image.", ephemeral=True)
                        return
                    data = await resp.read()
        except Exception as e:
            await interaction.followup.send(f"Failed: {e}", ephemeral=True)
            return
        try:
            emoji = await interaction.guild.create_custom_emoji(
                name=name, image=data, reason=f"By {interaction.user}"
            )
            await interaction.followup.send(embed=embed("✅ Emote", f"Added {emoji} `:{name}:`"))
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to create emoji: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCog(bot))
