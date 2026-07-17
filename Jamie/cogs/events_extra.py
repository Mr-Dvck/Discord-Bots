"""Background listeners: AFK pings, role persist, reminders."""

from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks


class ExtraEventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        db = self.bot.db
        if not db:
            return

        # Clear own AFK on message
        afk = await db.get_afk(message.author.id, message.guild.id)
        if afk:
            await db.clear_afk(message.author.id, message.guild.id)
            try:
                await message.channel.send(
                    f"Welcome back {message.author.mention} — AFK removed.",
                    delete_after=8,
                )
            except discord.HTTPException:
                pass

        # Mention AFK notice
        for user in message.mentions:
            status = await db.get_afk(user.id, message.guild.id)
            if status:
                try:
                    await message.channel.send(
                        f"💤 **{user.display_name}** is AFK: {status['message']}",
                        delete_after=12,
                    )
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        db = self.bot.db
        if not db:
            return
        role_ids = await db.get_role_persist(member.guild.id, member.id)
        roles = [member.guild.get_role(r) for r in role_ids]
        roles = [r for r in roles if r]
        if roles:
            try:
                await member.add_roles(*roles, reason="Role persist")
            except discord.HTTPException:
                pass

    @tasks.loop(seconds=30)
    async def reminder_loop(self):
        db = self.bot.db
        if not db:
            return
        now = datetime.now(timezone.utc).isoformat()
        try:
            due = await db.due_reminders(now)
        except Exception:
            return
        for r in due:
            channel = self.bot.get_channel(r["channel_id"])
            if channel:
                try:
                    await channel.send(
                        f"⏰ <@{r['user_id']}> reminder: {r['message']}"
                    )
                except discord.HTTPException:
                    pass
            await db.delete_reminder(r["id"])

    @reminder_loop.before_loop
    async def before_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ExtraEventsCog(bot))
