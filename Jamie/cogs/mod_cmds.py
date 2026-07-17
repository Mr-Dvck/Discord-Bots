"""Moderation slash commands from mod.csv (actions)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs._helpers import DANGER_COLOR, OK_COLOR, admin_check, embed, parse_duration


class ModCog(commands.GroupCog, group_name="mod"):
    """Core moderation actions (Administrator only)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
        # Entire /mod group requires Administrator
        self.interaction_check = self._admin_only  # type: ignore[method-assign]

    async def _admin_only(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise discord.app_commands.CheckFailure("Server only.")
        if not interaction.user.guild_permissions.administrator:
            raise discord.app_commands.CheckFailure("Administrator only.")
        return True

    async def _case(self, guild_id, user_id, mod_id, action, reason="", duration="", active=1):
        return await self.bot.db.add_case(guild_id, user_id, mod_id, action, reason, duration, active)

    @app_commands.command(name="kick", description="Kick a member")
    @admin_check()
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason"):
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Can't kick that member.", ephemeral=True)
            return
        await user.kick(reason=f"{interaction.user}: {reason}")
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "kick", reason)
        await interaction.response.send_message(
            embed=embed("👢 Kick", f"{user} kicked.\nReason: {reason}\nCase `#{case}`", DANGER_COLOR)
        )

    @app_commands.command(name="ban", description="Ban a member (optional time limit)")
    @app_commands.describe(duration="Optional e.g. 7d (stored as timed ban metadata)", delete_days="Delete message history days 0-7")
    @admin_check()
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member | discord.User,
        reason: str = "No reason",
        duration: str | None = None,
        delete_days: app_commands.Range[int, 0, 7] = 0,
    ):
        member = user if isinstance(user, discord.Member) else None
        if member and member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Can't ban that member.", ephemeral=True)
            return
        await interaction.guild.ban(user, reason=f"{interaction.user}: {reason}", delete_message_days=delete_days)
        case = await self._case(
            interaction.guild.id, user.id, interaction.user.id, "ban", reason, duration or "", 1 if duration else 1
        )
        await interaction.response.send_message(
            embed=embed(
                "🔨 Ban",
                f"{user} banned.\nReason: {reason}\nDuration: {duration or 'permanent'}\nCase `#{case}`",
                DANGER_COLOR,
            )
        )

    @app_commands.command(name="softban", description="Ban and immediate unban to delete user messages")
    @admin_check()
    async def softban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Softban"):
        await interaction.guild.ban(user, reason=f"{interaction.user}: {reason}", delete_message_days=1)
        await interaction.guild.unban(user, reason="Softban unban")
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "softban", reason)
        await interaction.response.send_message(
            embed=embed("💥 Softban", f"{user} softbanned.\nCase `#{case}`", DANGER_COLOR)
        )

    @app_commands.command(name="unban", description="Unban a member")
    @admin_check()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Unbanned"):
        try:
            uid = int(user_id)
        except ValueError:
            await interaction.response.send_message("Invalid user id.", ephemeral=True)
            return
        user = discord.Object(id=uid)
        try:
            await interaction.guild.unban(user, reason=f"{interaction.user}: {reason}")
        except discord.NotFound:
            await interaction.response.send_message("User is not banned.", ephemeral=True)
            return
        case = await self._case(interaction.guild.id, uid, interaction.user.id, "unban", reason, active=0)
        await interaction.response.send_message(embed=embed("✅ Unban", f"Unbanned `{uid}`.\nCase `#{case}`", OK_COLOR))

    @app_commands.command(name="mute", description="Mute a member so they cannot type")
    @app_commands.describe(duration="e.g. 10m, 1h, 1d (default 1h)")
    @admin_check()
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str = "1h",
        reason: str = "Muted",
    ):
        delta = parse_duration(duration) or timedelta(hours=1)
        until = datetime.now(timezone.utc) + delta
        try:
            await user.timeout(until, reason=f"{interaction.user}: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("Missing permission to timeout.", ephemeral=True)
            return
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "mute", reason, duration)
        await interaction.response.send_message(
            embed=embed("🔇 Mute", f"{user.mention} muted for **{duration}**.\nCase `#{case}`", DANGER_COLOR)
        )

    @app_commands.command(name="unmute", description="Unmute a member")
    @admin_check()
    async def unmute(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Unmuted"):
        await user.timeout(None, reason=f"{interaction.user}: {reason}")
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "unmute", reason, active=0)
        await interaction.response.send_message(
            embed=embed("🔊 Unmute", f"{user.mention} unmuted.\nCase `#{case}`", OK_COLOR)
        )

    @app_commands.command(name="deafen", description="Deafen a member")
    @admin_check()
    async def deafen(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Deafened"):
        if not user.voice:
            await interaction.response.send_message("User is not in a voice channel.", ephemeral=True)
            return
        await user.edit(deafen=True, reason=f"{interaction.user}: {reason}")
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "deafen", reason)
        await interaction.response.send_message(
            embed=embed("Deafened", f"{user.mention} deafened.\nCase `#{case}`")
        )

    @app_commands.command(name="undeafen", description="Undeafen a member")
    @admin_check()
    async def undeafen(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Undeafened"):
        if not user.voice:
            await interaction.response.send_message("User is not in a voice channel.", ephemeral=True)
            return
        await user.edit(deafen=False, reason=f"{interaction.user}: {reason}")
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "undeafen", reason, active=0)
        await interaction.response.send_message(embed=embed("Undeafen", f"{user.mention} undeafened.\nCase `#{case}`"))

    @app_commands.command(name="warn", description="Warn a member")
    @admin_check()
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Warned"):
        warn_id = await self.bot.db.add_warning(interaction.guild.id, user.id, interaction.user.id, reason)
        case = await self._case(interaction.guild.id, user.id, interaction.user.id, "warn", reason)
        warnings = await self.bot.db.get_warnings(interaction.guild.id, user.id)
        await interaction.response.send_message(
            embed=embed(
                "⚠️ Warn",
                f"{user.mention} warned.\nReason: {reason}\nWarn `#{warn_id}` · Case `#{case}`\nTotal: **{len(warnings)}**",
                DANGER_COLOR,
            )
        )

    @app_commands.command(name="clean", description="Clean up bot responses")
    @app_commands.describe(amount="How many recent bot messages to delete (1-50)")
    @admin_check()
    async def clean(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 50] = 20):
        await interaction.response.defer(ephemeral=True)
        me = interaction.guild.me

        def check(m: discord.Message):
            return m.author.id == me.id or (m.author.bot and "jamie" in (m.author.name or "").lower())

        deleted = await interaction.channel.purge(limit=amount * 2, check=check)
        # only count up to amount
        await interaction.followup.send(
            embed=embed("🧹 Clean", f"Removed **{min(len(deleted), amount)}** bot messages."),
            ephemeral=True,
        )

    @app_commands.command(name="members", description="List members in a role(s) (max 90)")
    @admin_check()
    async def members(self, interaction: discord.Interaction, role: discord.Role):
        members = role.members[:90]
        if not members:
            await interaction.response.send_message(embed=embed("👥 Members", f"No members in {role.mention}."))
            return
        lines = [f"• {m} (`{m.id}`)" for m in members]
        await interaction.response.send_message(
            embed=embed(f"👥 {role.name} ({len(role.members)})", "\n".join(lines)[:4000])
        )

    @app_commands.command(name="diagnose", description="Diagnose any command or module for problems")
    @admin_check()
    async def diagnose(self, interaction: discord.Interaction, name: str):
        me = interaction.guild.me
        issues = []
        perms = interaction.channel.permissions_for(me) if interaction.channel else None
        if perms:
            for p in ("send_messages", "embed_links", "manage_messages", "moderate_members", "kick_members", "ban_members"):
                if not getattr(perms, p, False):
                    issues.append(f"Missing channel/guild perm: `{p}`")
        s = await self.bot.db.get_guild_settings(interaction.guild.id)
        cmds = s.get("commands") or {}
        mods = s.get("modules") or {}
        key = name.lower()
        if key in cmds and cmds[key] is False:
            issues.append(f"Command `{key}` is disabled via `/manage command`.")
        if key in mods and mods[key] is False:
            issues.append(f"Module `{key}` is disabled via `/manage module`.")
        registered = {c.qualified_name for c in self.bot.tree.walk_commands()}
        if key not in {n.split()[-1] for n in registered} and key not in mods and f"mod {key}" not in registered:
            issues.append(f"No exact match for `{key}` in registered commands (may still be a subcommand).")
        if not issues:
            issues.append("No obvious problems found. Permissions look OK for common mod actions.")
        await interaction.response.send_message(embed=embed(f"🩺 Diagnose: {name}", "\n".join(f"• {i}" for i in issues)))

    @app_commands.command(name="rolepersist", description="Assign/unassign a role that persists if user leaves/rejoins")
    @admin_check()
    async def rolepersist(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        ids = await self.bot.db.get_role_persist(interaction.guild.id, user.id)
        if role.id in ids:
            ids = [i for i in ids if i != role.id]
            await self.bot.db.set_role_persist(interaction.guild.id, user.id, ids)
            if role in user.roles:
                await user.remove_roles(role, reason="Role persist off")
            await interaction.response.send_message(
                embed=embed("📌 Role Persist", f"Removed persist for {role.mention} on {user.mention}.")
            )
        else:
            ids.append(role.id)
            await self.bot.db.set_role_persist(interaction.guild.id, user.id, ids)
            if role not in user.roles:
                await user.add_roles(role, reason="Role persist on")
            await interaction.response.send_message(
                embed=embed("📌 Role Persist", f"{role.mention} will persist for {user.mention}.")
            )

    @app_commands.command(name="temprole", description="Assign/unassign a temporary role")
    @app_commands.describe(duration="How long to keep the role e.g. 1h")
    @admin_check()
    async def temprole(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        role: discord.Role,
        duration: str = "1h",
    ):
        delta = parse_duration(duration)
        if not delta:
            await interaction.response.send_message("Invalid duration.", ephemeral=True)
            return
        await user.add_roles(role, reason=f"Temp role {duration}")
        case = await self._case(
            interaction.guild.id, user.id, interaction.user.id, "temprole", role.name, duration
        )
        await interaction.response.send_message(
            embed=embed("⏳ Temp Role", f"Gave {user.mention} {role.mention} for **{duration}**.\nCase `#{case}`")
        )

        async def remove_later():
            await discord.utils.sleep_until(datetime.now(timezone.utc) + delta)
            try:
                member = interaction.guild.get_member(user.id)
                if member and role in member.roles:
                    await member.remove_roles(role, reason="Temp role expired")
            except Exception:
                pass

        interaction.client.loop.create_task(remove_later())

    @app_commands.command(name="lock", description="Lock a channel with optional timer")
    @app_commands.describe(duration="Optional unlock after e.g. 10m")
    @admin_check()
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        duration: str | None = None,
        reason: str = "Locked",
    ):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
        case = await self._case(interaction.guild.id, 0, interaction.user.id, "lock", f"{channel.id}:{reason}", duration or "")
        await interaction.response.send_message(
            embed=embed("🔒 Lock", f"{channel.mention} locked.\nCase `#{case}`")
        )
        if duration:
            delta = parse_duration(duration)
            if delta:

                async def unlock_later():
                    await discord.utils.sleep_until(datetime.now(timezone.utc) + delta)
                    ow = channel.overwrites_for(interaction.guild.default_role)
                    ow.send_messages = None
                    try:
                        await channel.set_permissions(interaction.guild.default_role, overwrite=ow, reason="Auto unlock")
                    except Exception:
                        pass

                interaction.client.loop.create_task(unlock_later())

    @app_commands.command(name="unlock", description="Unlock a previously locked channel")
    @admin_check()
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason="Unlocked")
        await interaction.response.send_message(embed=embed("🔓 Unlock", f"{channel.mention} unlocked.", OK_COLOR))

    @app_commands.command(name="lockdown", description="Lock channels defined in moderation settings")
    @admin_check()
    async def lockdown(self, interaction: discord.Interaction, reason: str = "Lockdown"):
        # Lock current category channels or current channel if no category
        await interaction.response.defer()
        targets = []
        if isinstance(interaction.channel, discord.TextChannel) and interaction.channel.category:
            targets = [c for c in interaction.channel.category.channels if isinstance(c, discord.TextChannel)]
        else:
            targets = [interaction.channel]
        locked = 0
        for ch in targets:
            try:
                ow = ch.overwrites_for(interaction.guild.default_role)
                ow.send_messages = False
                await ch.set_permissions(interaction.guild.default_role, overwrite=ow, reason=reason)
                locked += 1
            except Exception:
                pass
        case = await self._case(interaction.guild.id, 0, interaction.user.id, "lockdown", reason)
        await interaction.followup.send(
            embed=embed("🚨 Lockdown", f"Locked **{locked}** channel(s).\nCase `#{case}`", DANGER_COLOR)
        )

    @app_commands.command(name="ignored", description="List ignored users, roles, and channels")
    @admin_check()
    async def ignored(self, interaction: discord.Interaction):
        rows = await self.bot.db.list_ignores(interaction.guild.id)
        if not rows:
            await interaction.response.send_message(embed=embed("🙈 Ignored", "Nothing ignored."))
            return
        lines = [f"• `{r['target_type']}` `{r['target_id']}`" for r in rows]
        await interaction.response.send_message(embed=embed("🙈 Ignored", "\n".join(lines)))

    @app_commands.command(name="moderations", description="Get a list of active timed moderations")
    @admin_check()
    async def moderations(self, interaction: discord.Interaction):
        rows = await self.bot.db.get_active_moderations(interaction.guild.id)
        timed = [r for r in rows if r.get("duration")]
        if not timed:
            await interaction.response.send_message(embed=embed("⏳ Active Mods", "No active timed moderations."))
            return
        lines = [
            f"• Case `#{r['id']}` **{r['action']}** user `{r['user_id']}` · {r['duration']} — {r['reason'] or '—'}"
            for r in timed[:25]
        ]
        await interaction.response.send_message(embed=embed("⏳ Active Moderations", "\n".join(lines)))

    @app_commands.command(name="duration", description="Change the duration of a mute/ban")
    @admin_check()
    async def duration(self, interaction: discord.Interaction, case_id: int, duration: str):
        ok = await self.bot.db.set_case_duration(interaction.guild.id, case_id, duration)
        if not ok:
            await interaction.response.send_message("Case not found.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=embed("⏱️ Duration", f"Case `#{case_id}` duration set to **{duration}**.")
        )

    @app_commands.command(name="star", description="View starboard stats for a message")
    @admin_check()
    async def star(self, interaction: discord.Interaction, message_id: str):
        try:
            mid = int(message_id)
        except ValueError:
            await interaction.response.send_message("Invalid message id.", ephemeral=True)
            return
        try:
            msg = await interaction.channel.fetch_message(mid)
        except discord.NotFound:
            await interaction.response.send_message("Message not found in this channel.", ephemeral=True)
            return
        stars = 0
        for r in msg.reactions:
            if str(r.emoji) in ("⭐", "🌟"):
                stars += r.count
        await interaction.response.send_message(
            embed=embed(
                "⭐ Starboard",
                f"Message `{mid}` by {msg.author.mention}\n⭐ count: **{stars}**\nJump: {msg.jump_url}",
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ModCog(bot))
