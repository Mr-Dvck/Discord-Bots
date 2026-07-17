"""
MemoryCog — Monitors all messages, builds user profiles, maintains server map.
Runs background tasks for personality analysis and memory pruning.
"""

import discord
from discord.ext import commands, tasks
import logging
from datetime import datetime, timezone

log = logging.getLogger("jamie.memory")

# How often to run personality analysis (minutes)
PERSONALITY_ANALYSIS_INTERVAL = 30
# Minimum messages before analyzing personality
MIN_MESSAGES_FOR_ANALYSIS = 15
# Max messages to keep per guild
MAX_MESSAGES_PER_GUILD = 5000


class MemoryCog(commands.Cog):
    """Message monitoring, user profiling, and server cartography."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._recent_joins: set[int] = set()

    # ── on_message — store every message ───────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Store every non-bot message for memory and profiling."""
        if message.author.bot or not message.guild:
            return

        db = self.bot.db
        guild_id = message.guild.id
        user_id = message.author.id

        # Store the message
        await db.store_message(
            message_id=message.id,
            guild_id=guild_id,
            channel_id=message.channel.id,
            channel_name=message.channel.name,
            user_id=user_id,
            username=message.author.name,
            content=message.content,
        )

        # Update user profile
        await db.increment_message_count(user_id, guild_id)
        await db.upsert_user(
            user_id=user_id,
            guild_id=guild_id,
            username=message.author.name,
            display_name=message.author.display_name,
            avatar_url=message.author.display_avatar.url if message.author.display_avatar else "",
            last_seen=datetime.now(timezone.utc).isoformat(),
        )

    # ── on_member_join — register new members ────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Register new members when they join."""
        if member.bot:
            return

        db = self.bot.db
        await db.upsert_user(
            user_id=member.id,
            guild_id=member.guild.id,
            username=member.name,
            display_name=member.display_name,
            avatar_url=member.display_avatar.url if member.display_avatar else "",
            joined_at=member.joined_at.isoformat() if member.joined_at else "",
            last_seen=datetime.now(timezone.utc).isoformat(),
        )
        # Join banners are handled by WelcomeCog (Dyno-style), not here.

    # ── on_member_remove — note departure ─────────────────────────

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Note when members leave."""
        if member.bot:
            return

        db = self.bot.db
        profile = await db.get_user_profile(member.id, member.guild.id)
        if profile:
            notes = profile.get("notes", "")
            notes += f"\n[Left server: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}]"
            await db.update_user_notes(member.id, member.guild.id, notes)

    # ── on_guild_channel_create/update/delete — server map ────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Update server map when channels are created."""
        if not hasattr(channel, 'guild') or not channel.guild:
            return
        db = self.bot.db
        category = channel.category.name if channel.category else "No Category"
        ch_type = "text" if isinstance(channel, discord.TextChannel) else \
                  "voice" if isinstance(channel, discord.VoiceChannel) else \
                  "category" if isinstance(channel, discord.CategoryChannel) else "other"

        topic = channel.topic if isinstance(channel, discord.TextChannel) else ""
        await db.upsert_channel(
            guild_id=channel.guild.id,
            channel_id=channel.id,
            channel_name=channel.name,
            channel_type=ch_type,
            category_name=category,
            topic=topic or "",
            position=channel.position,
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """Update server map when channels are updated."""
        if not hasattr(after, 'guild') or not after.guild:
            return
        db = self.bot.db
        category = after.category.name if after.category else "No Category"
        ch_type = "text" if isinstance(after, discord.TextChannel) else \
                  "voice" if isinstance(after, discord.VoiceChannel) else \
                  "category" if isinstance(after, discord.CategoryChannel) else "other"

        topic = after.topic if isinstance(after, discord.TextChannel) else ""
        await db.upsert_channel(
            guild_id=after.guild.id,
            channel_id=after.id,
            channel_name=after.name,
            channel_type=ch_type,
            category_name=category,
            topic=topic or "",
            position=after.position,
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Remove from server map when channels are deleted."""
        if not hasattr(channel, 'guild') or not channel.guild:
            return
        db = self.bot.db
        await db.delete_channel(channel.id)

    # ── on_member_update — track name changes ─────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Track username/nickname changes."""
        if before.display_name != after.display_name or before.name != after.name:
            db = self.bot.db
            await db.upsert_user(
                user_id=after.id,
                guild_id=after.guild.id,
                username=after.name,
                display_name=after.display_name,
                avatar_url=after.display_avatar.url if after.display_avatar else "",
                last_seen=datetime.now(timezone.utc).isoformat(),
            )

    # ── background tasks ──────────────────────────────────────────

    async def cog_load(self):
        """Start background tasks when cog loads."""
        self._personality_loop.start()
        self._prune_loop.start()

    async def cog_unload(self):
        """Stop background tasks when cog unloads."""
        self._personality_loop.cancel()
        self._prune_loop.cancel()

    @tasks.loop(minutes=PERSONALITY_ANALYSIS_INTERVAL)
    async def _personality_loop(self):
        """Periodically analyze user personalities from their messages."""
        log.info("Running personality analysis cycle")
        db = self.bot.db

        for guild in self.bot.guilds:
            profiles = await db.get_all_profiles(guild.id)
            for profile in profiles:
                if profile["message_count"] < MIN_MESSAGES_FOR_ANALYSIS:
                    continue
                if profile["personality_summary"] and profile["message_count"] % 50 != 0:
                    # Only re-analyze every 50 messages after initial analysis
                    continue

                messages = await db.get_user_messages(profile["user_id"], guild.id, limit=30)
                if not messages:
                    continue

                contents = [m["content"] for m in messages]
                try:
                    analysis = await self.bot.llm.analyze_user_personality(contents)
                    await db.update_user_personality(
                        profile["user_id"], guild.id,
                        analysis.get("summary", ""),
                        analysis.get("interests", ""),
                    )
                    log.debug("Updated personality for user %d in guild %d",
                             profile["user_id"], guild.id)
                except Exception as e:
                    log.error("Personality analysis failed for user %d: %s",
                             profile["user_id"], e)

    @tasks.loop(minutes=60)
    async def _prune_loop(self):
        """Periodically prune old messages to keep memory manageable."""
        log.info("Running memory prune cycle")
        db = self.bot.db
        for guild in self.bot.guilds:
            await db.prune_old_messages(guild.id, keep=MAX_MESSAGES_PER_GUILD)

    @_personality_loop.before_loop
    async def _before_personality(self):
        await self.bot.wait_until_ready()

    @_prune_loop.before_loop
    async def _before_prune(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryCog(bot))
