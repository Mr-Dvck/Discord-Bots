"""
SetupCog — Handles initial server setup when Jamie joins a guild.
Sets the dedicated channel and registers the server.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

log = logging.getLogger("jamie.setup")


class SetupCog(commands.Cog):
    """First-run setup and channel configuration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── on_guild_join — auto-setup prompt ─────────────────────────

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """When Jamie joins a new server, find the owner and send setup instructions."""
        log.info("Joined guild: %s (%d)", guild.name, guild.id)

        # Try to DM the server owner
        try:
            owner = guild.owner
            if owner:
                embed = discord.Embed(
                    title="🛸 Jamie just landed.",
                    description=(
                        f"Yo, I'm Jamie. I just touched down in **{guild.name}**.\n\n"
                        "Before I can do anything, I need a **dedicated channel** to live in. "
                        "Use `/setup` in any channel I can see, or an admin can run it.\n\n"
                        "Once set up, I'll:\n"
                        "• Memorize every username and build profiles on everyone\n"
                        "• Cartograph the entire server (channels, categories, roles)\n"
                        "• Monitor conversations so I can reference things later\n"
                        "• Respond in my dedicated channel or when @mentioned\n"
                        "• Generate images on command\n\n"
                        "Run `/setup` to get started."
                    ),
                    color=0x39B7C4,
                )
                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                await owner.send(embed=embed)
        except discord.Forbidden:
            log.warning("Cannot DM owner of %s, will wait for /setup", guild.name)

        # Also try to find a system channel or general channel to send a message
        target = guild.system_channel
        if not target:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    target = ch
                    break

        if target:
            embed = discord.Embed(
                title="🛸 Jamie just landed.",
                description=(
                    "I need a **dedicated channel** to operate from. "
                    "An admin needs to run `/setup` to set my home channel.\n\n"
                    "Until then, I'm just vibing in the void."
                ),
                color=0x39B7C4,
            )
            try:
                await target.send(embed=embed)
            except discord.Forbidden:
                pass

    # ── /setup command ────────────────────────────────────────────

    @app_commands.command(
        name="setup",
        description="Set Jamie's dedicated channel (admin only)"
    )
    @app_commands.describe(channel="The channel where Jamie will live and respond")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = self.bot.db

        # Check bot can see and send in that channel
        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.send_messages and perms.view_channel and perms.embed_links):
            await interaction.response.send_message(
                f"❌ I can't properly operate in {channel.mention} — I need "
                "View Channel, Send Messages, and Embed Links permissions there.",
                ephemeral=True,
            )
            return

        await db.set_channel(interaction.guild.id, channel.id)

        embed = discord.Embed(
            title="✅ Jamie is set up",
            description=(
                f"My home channel is now {channel.mention}\n\n"
                "Here's what happens next:\n"
                "• I'll start memorizing everyone who talks\n"
                "• I'll map out the entire server structure\n"
                "• I'll monitor conversations and build profiles\n"
                "• Talk to me here, or @ me anywhere else\n\n"
                "Let's go. 🔥"
            ),
            color=0x7DD3A7,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

        # Send a welcome message in the dedicated channel
        welcome = discord.Embed(
            title="🔥 Jamie is online",
            description=(
                "This is my crib now. Come talk to me here anytime — "
                "or @ me in other channels and I'll pull up.\n\n"
                "Try `/help` to see what I can do."
            ),
            color=0x39B7C4,
        )
        try:
            await channel.send(embed=welcome)
        except discord.Forbidden:
            pass

        # Trigger initial server cartography
        await self._cartograph_server(interaction.guild)

    # ── /setchannel — change Jamie's channel ──────────────────────

    @app_commands.command(
        name="setchannel",
        description="Change Jamie's dedicated channel (admin only)"
    )
    @app_commands.describe(channel="The new channel for Jamie")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db = self.bot.db
        await db.set_channel(interaction.guild.id, channel.id)

        await interaction.response.send_message(
            f"✅ My home channel is now {channel.mention}",
            ephemeral=True,
        )

    # ── server cartography ────────────────────────────────────────

    async def _cartograph_server(self, guild: discord.Guild):
        """Map out the entire server structure."""
        db = self.bot.db
        log.info("Cartographing server: %s (%d)", guild.name, guild.id)

        for ch in guild.channels:
            if isinstance(ch, discord.TextChannel):
                category = ch.category.name if ch.category else "No Category"
                await db.upsert_channel(
                    guild_id=guild.id,
                    channel_id=ch.id,
                    channel_name=ch.name,
                    channel_type="text",
                    category_name=category,
                    topic=ch.topic or "",
                    position=ch.position,
                )
            elif isinstance(ch, discord.VoiceChannel):
                category = ch.category.name if ch.category else "No Category"
                await db.upsert_channel(
                    guild_id=guild.id,
                    channel_id=ch.id,
                    channel_name=ch.name,
                    channel_type="voice",
                    category_name=category,
                    position=ch.position,
                )
            elif isinstance(ch, discord.CategoryChannel):
                await db.upsert_channel(
                    guild_id=guild.id,
                    channel_id=ch.id,
                    channel_name=ch.name,
                    channel_type="category",
                    position=ch.position,
                )

        # Register all existing members
        for member in guild.members:
            if member.bot:
                continue
            await db.upsert_user(
                user_id=member.id,
                guild_id=guild.id,
                username=member.name,
                display_name=member.display_name,
                avatar_url=member.display_avatar.url if member.display_avatar else "",
                joined_at=member.joined_at.isoformat() if member.joined_at else "",
                last_seen=discord.utils.utcnow().isoformat(),
            )

        log.info("Cartographed %d channels and %d members for %s",
                 len(guild.channels), len([m for m in guild.members if not m.bot]),
                 guild.name)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
