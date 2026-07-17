"""
Counting game — any text channel whose topic contains [jamie:counting]
is moderated as a count-up game by Jamie (admin bot).

Dashboard tool setup_counting_game creates/configures these channels.
"""

from __future__ import annotations

import logging
import re

import discord
from discord.ext import commands

log = logging.getLogger("jamie.counting")

MARKER = "[jamie:counting]"
# Optional: [jamie:counting start=1]
START_RE = re.compile(r"\[jamie:counting(?:\s+start=(\d+))?\]", re.I)
ONLY_NUMBER = re.compile(r"^\s*(\d+)\s*$")


class CountingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # channel_id -> {"next": int, "last_user": int | None}
        self._state: dict[int, dict] = {}

    def _is_counting_channel(self, channel: discord.abc.Messageable) -> bool:
        if not isinstance(channel, discord.TextChannel):
            return False
        topic = channel.topic or ""
        return MARKER.lower() in topic.lower() or bool(START_RE.search(topic))

    def _start_from_topic(self, topic: str | None) -> int:
        if not topic:
            return 1
        m = START_RE.search(topic)
        if m and m.group(1):
            return max(1, int(m.group(1)))
        return 1

    def _get_state(self, channel: discord.TextChannel) -> dict:
        st = self._state.get(channel.id)
        if not st:
            start = self._start_from_topic(channel.topic)
            st = {"next": start, "last_user": None}
            self._state[channel.id] = st
        return st

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        if not self._is_counting_channel(message.channel):
            return

        # Don't fight with Jamie's main chat channel responses for non-numbers
        content = message.content or ""
        m = ONLY_NUMBER.match(content)
        st = self._get_state(message.channel)

        if not m:
            try:
                await message.add_reaction("❌")
                await message.reply(
                    f"Only the next number (**{st['next']}**). Nothing else.",
                    delete_after=8,
                    mention_author=False,
                )
            except discord.HTTPException:
                pass
            return

        number = int(m.group(1))
        expected = st["next"]

        if st["last_user"] is not None and st["last_user"] == message.author.id:
            try:
                await message.add_reaction("❌")
                await message.reply(
                    "Same person can't count twice in a row.",
                    delete_after=8,
                    mention_author=False,
                )
            except discord.HTTPException:
                pass
            return

        if number != expected:
            # Reset to start
            start = self._start_from_topic(message.channel.topic)
            st["next"] = start
            st["last_user"] = None
            try:
                await message.add_reaction("❌")
                await message.reply(
                    f"Wrong — needed **{expected}**. Reset to **{start}**.",
                    delete_after=12,
                    mention_author=False,
                )
            except discord.HTTPException:
                pass
            return

        # Success
        st["next"] = expected + 1
        st["last_user"] = message.author.id
        try:
            await message.add_reaction("✅")
        except discord.HTTPException:
            pass

        # Milestone flex
        if expected > 0 and expected % 100 == 0:
            try:
                await message.channel.send(
                    f"🔥 **{expected}** — {message.author.display_name} locked it in. Next is **{st['next']}**."
                )
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """Reset in-memory state if counting topic changes."""
        if not isinstance(after, discord.TextChannel):
            return
        if before.topic != after.topic and after.id in self._state:
            del self._state[after.id]
            log.info("Cleared counting state for channel %s", after.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(CountingCog(bot))
