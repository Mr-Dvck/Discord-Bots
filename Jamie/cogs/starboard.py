"""
Starboard Cog for Jamie Bot
Allows users to star messages and compiles them into a designated starboard channel.
"""

from __future__ import annotations

import logging
import discord
from discord.ext import commands

log = logging.getLogger("jamie.starboard")


class StarboardCog(commands.Cog):
    """Starboard module — reactions system that highlights good posts."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐":
            return

        db = getattr(self.bot, "db", None)
        if not db:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        cfg = await db.get_starboard_config(guild.id)
        if not cfg.get("enabled") or not cfg.get("channel_id"):
            return

        starboard_channel = guild.get_channel(cfg["channel_id"])
        if not starboard_channel:
            try:
                starboard_channel = await self.bot.fetch_channel(cfg["channel_id"])
            except (discord.HTTPException, discord.NotFound):
                log.warning("Starboard channel %s missing for guild %s", cfg["channel_id"], guild.id)
                return

        if not isinstance(starboard_channel, discord.TextChannel):
            return

        # Fetch original message
        orig_channel = guild.get_channel(payload.channel_id)
        if not orig_channel or not isinstance(orig_channel, discord.TextChannel):
            return

        try:
            msg = await orig_channel.fetch_message(payload.message_id)
        except (discord.HTTPException, discord.NotFound):
            return

        if msg.author.bot:
            return

        reaction = discord.utils.get(msg.reactions, emoji="⭐")
        star_count = reaction.count if reaction else 0
        min_stars = cfg.get("min_stars") or 3

        if star_count < min_stars:
            return

        starboard_msg_id = await db.get_starboard_message(msg.id)
        embed = self._create_starboard_embed(msg)

        content = f"⭐ **{star_count}** | {orig_channel.mention}"

        if starboard_msg_id:
            try:
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                await starboard_msg.edit(content=content, embed=embed)
            except discord.NotFound:
                # Starboard message deleted manually, create a new one
                new_starboard_msg = await starboard_channel.send(content=content, embed=embed)
                await db.save_starboard_message(msg.id, new_starboard_msg.id)
            except discord.HTTPException:
                log.exception("Failed to edit starboard message %s", starboard_msg_id)
        else:
            try:
                new_starboard_msg = await starboard_channel.send(content=content, embed=embed)
                await db.save_starboard_message(msg.id, new_starboard_msg.id)
            except discord.HTTPException:
                log.exception("Failed to send starboard message for original message %s", msg.id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐":
            return

        db = getattr(self.bot, "db", None)
        if not db:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        cfg = await db.get_starboard_config(guild.id)
        if not cfg.get("enabled") or not cfg.get("channel_id"):
            return

        starboard_channel = guild.get_channel(cfg["channel_id"])
        if not starboard_channel:
            try:
                starboard_channel = await self.bot.fetch_channel(cfg["channel_id"])
            except (discord.HTTPException, discord.NotFound):
                return

        if not isinstance(starboard_channel, discord.TextChannel):
            return

        starboard_msg_id = await db.get_starboard_message(payload.message_id)
        if not starboard_msg_id:
            return

        orig_channel = guild.get_channel(payload.channel_id)
        if not orig_channel or not isinstance(orig_channel, discord.TextChannel):
            return

        try:
            msg = await orig_channel.fetch_message(payload.message_id)
            reaction = discord.utils.get(msg.reactions, emoji="⭐")
            star_count = reaction.count if reaction else 0
        except (discord.HTTPException, discord.NotFound):
            star_count = 0

        min_stars = cfg.get("min_stars") or 3

        if star_count < min_stars:
            # Remove from starboard
            try:
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                await starboard_msg.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException:
                log.exception("Failed to delete starboard message %s", starboard_msg_id)
            
            await db.delete_starboard_message(payload.message_id)
        else:
            # Update count
            try:
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                content = f"⭐ **{star_count}** | {orig_channel.mention}"
                embed = self._create_starboard_embed(msg)
                await starboard_msg.edit(content=content, embed=embed)
            except discord.NotFound:
                await db.delete_starboard_message(payload.message_id)
            except discord.HTTPException:
                log.exception("Failed to update starboard message %s", starboard_msg_id)

    def _create_starboard_embed(self, msg: discord.Message) -> discord.Embed:
        embed = discord.Embed(
            description=msg.content or "",
            color=0xFFAC33,  # Star gold color
            timestamp=msg.created_at,
        )
        embed.set_author(
            name=msg.author.display_name,
            icon_url=msg.author.display_url or msg.author.default_avatar.url,
        )
        embed.add_field(
            name="Source",
            value=f"[Jump to message]({msg.jump_url})",
            inline=True,
        )
        embed.set_footer(text=f"ID: {msg.id}")

        # Handle message attachments (like images)
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    embed.set_image(url=attachment.url)
                    break

        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(StarboardCog(bot))
