"""
UtilityCog — /profile, /servermap, /remember, /help, and other utility commands.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timezone

log = logging.getLogger("jamie.utility")


class UtilityCog(commands.Cog):
    """Utility and information commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /profile — view a user's profile ─────────────────────────

    @app_commands.command(
        name="profile",
        description="View Jamie's profile on a user"
    )
    @app_commands.describe(user="The user to look up (defaults to yourself)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        """View Jamie's profile on a user."""
        db = self.bot.db
        target = user or interaction.user

        profile_data = await db.get_user_profile(target.id, interaction.guild_id)

        if not profile_data:
            await interaction.response.send_message(
                f"I don't have any data on **{target.display_name}** yet. "
                "They probably haven't talked enough for me to notice them.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"📋 Profile: {target.display_name}",
            color=0x39B7C4,
        )
        embed.set_thumbnail(url=target.display_avatar.url if target.display_avatar else "")

        embed.add_field(
            name="Username",
            value=f"@{profile_data['username']}",
            inline=True,
        )
        embed.add_field(
            name="Messages",
            value=str(profile_data["message_count"]),
            inline=True,
        )
        embed.add_field(
            name="Last Seen",
            value=profile_data["last_seen"][:10] if profile_data["last_seen"] else "Unknown",
            inline=True,
        )

        if profile_data["personality_summary"]:
            embed.add_field(
                name="Personality",
                value=profile_data["personality_summary"][:300],
                inline=False,
            )

        if profile_data["interests"]:
            embed.add_field(
                name="Interests",
                value=profile_data["interests"][:200],
                inline=False,
            )

        if profile_data["notes"]:
            embed.add_field(
                name="Notes",
                value=profile_data["notes"][:300],
                inline=False,
            )

        embed.set_footer(text=f"Joined: {profile_data['joined_at'][:10] if profile_data['joined_at'] else 'Unknown'}")

        await interaction.response.send_message(embed=embed)

    # ── /servermap — view the server map ──────────────────────────

    @app_commands.command(
        name="servermap",
        description="View Jamie's map of the server structure"
    )
    async def servermap(self, interaction: discord.Interaction):
        """View the server map Jamie has built."""
        db = self.bot.db
        channels = await db.get_server_map(interaction.guild_id)

        if not channels:
            await interaction.response.send_message(
                "I haven't mapped this server yet. Try running `/setup` first.",
                ephemeral=True,
            )
            return

        # Group by category
        categories: dict[str, list] = {}
        no_category = []
        for ch in channels:
            cat = ch["category_name"] or "No Category"
            if ch["channel_type"] == "category":
                continue  # Skip category entries themselves
            if cat == "No Category":
                no_category.append(ch)
            else:
                categories.setdefault(cat, []).append(ch)

        # Build the map text
        lines = [f"🗺️ **{interaction.guild.name}** — Server Map\n"]

        for cat_name, cat_channels in sorted(categories.items()):
            lines.append(f"📁 **{cat_name}**")
            for ch in cat_channels:
                icon = "💬" if ch["channel_type"] == "text" else "🔊" if ch["channel_type"] == "voice" else "📌"
                topic = f" — *{ch['topic'][:50]}*" if ch["topic"] else ""
                lines.append(f"  {icon} #{ch['channel_name']}{topic}")
            lines.append("")

        if no_category:
            lines.append("📁 **No Category**")
            for ch in no_category:
                icon = "💬" if ch["channel_type"] == "text" else "🔊" if ch["channel_type"] == "voice" else "📌"
                lines.append(f"  {icon} #{ch['channel_name']}")
            lines.append("")

        # Add stats
        profiles = await db.get_all_profiles(interaction.guild_id)
        total_messages = sum(p["message_count"] for p in profiles)
        lines.append(f"📊 **Stats:** {len(profiles)} users tracked | {total_messages} messages memorized | {len(channels)} channels mapped")

        map_text = "\n".join(lines)

        if len(map_text) > 2000:
            # Send as multiple messages
            chunks = []
            current = ""
            for line in lines:
                if len(current) + len(line) + 1 > 1900:
                    chunks.append(current)
                    current = line
                else:
                    current += "\n" + line if current else line
            if current:
                chunks.append(current)

            await interaction.response.send_message(chunks[0])
            for chunk in chunks[1:]:
                await interaction.followup.send(chunk)
        else:
            await interaction.response.send_message(map_text)

    # ── /remember — search Jamie's memory ──────────────────────────

    @app_commands.command(
        name="remember",
        description="Search Jamie's memory for something"
    )
    @app_commands.describe(query="What to search for")
    async def remember(self, interaction: discord.Interaction, query: str):
        """Search Jamie's message memory."""
        db = self.bot.db

        results = await db.search_messages(interaction.guild_id, query, limit=10)

        if not results:
            await interaction.response.send_message(
                f"I don't remember anything about \"{query}\". Either nobody said it, or it was before my time.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"🧠 Memory: \"{query}\"",
            description=f"Found {len(results)} results",
            color=0x39B7C4,
        )

        for i, msg in enumerate(results[:8]):
            timestamp = msg["timestamp"][:16] if msg["timestamp"] else "Unknown"
            embed.add_field(
                name=f"#{i+1} — {msg['username']} in #{msg['channel_name']}",
                value=f"[{timestamp}] {msg['content'][:150]}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # ── /note — add a note to a user's profile ────────────────────

    @app_commands.command(
        name="note",
        description="Add a note to a user's profile (admin only)"
    )
    @app_commands.describe(
        user="The user to add a note to",
        note="The note to add"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def note(self, interaction: discord.Interaction, user: discord.Member, note: str):
        """Add a note to a user's profile."""
        db = self.bot.db

        profile = await db.get_user_profile(user.id, interaction.guild_id)
        existing = profile["notes"] if profile else ""
        new_notes = f"{existing}\n[{interaction.user.display_name}]: {note}" if existing else f"[{interaction.user.display_name}]: {note}"

        await db.update_user_notes(user.id, interaction.guild_id, new_notes)

        await interaction.response.send_message(
            f"📝 Note added to **{user.display_name}**'s profile.",
            ephemeral=True,
        )

    # ── /help — show all commands ─────────────────────────────────

    @app_commands.command(
        name="help",
        description="Show all of Jamie's commands"
    )
    async def help(self, interaction: discord.Interaction):
        """Show Jamie's command list."""
        embed = discord.Embed(
            title="🔥 Jamie Commands",
            description="Here's everything I can do. Talk to me in my channel or @ me anywhere.",
            color=0x39B7C4,
        )

        embed.add_field(
            name="🛸 Setup",
            value=(
                "`/setup` — Set my dedicated channel (admin)\n"
                "`/setchannel` — Change my channel (admin)"
            ),
            inline=False,
        )

        embed.add_field(
            name="💬 Chat",
            value=(
                "`/talk <message>` — Talk to me directly\n"
                "`/ask <query>` — Ask about someone/something\n"
                "@Jamie — Mention me anywhere to talk"
            ),
            inline=False,
        )

        embed.add_field(
            name="🎨 Images",
            value=(
                "`/generate <prompt>` — Generate an image\n"
                "`/imagine` — I imagine something wild"
            ),
            inline=False,
        )

        embed.add_field(
            name="🧠 Memory",
            value=(
                "`/profile [user]` — View a user's profile\n"
                "`/servermap` — View the server map\n"
                "`/remember <query>` — Search my memory\n"
                "`/note <user> <note>` — Add a note (admin)"
            ),
            inline=False,
        )

        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else "")
        embed.set_footer(text="Jamie remembers everything. 🔥")

        await interaction.response.send_message(embed=embed)

    # ── /stats — bot statistics ────────────────────────────────────

    @app_commands.command(
        name="stats",
        description="View Jamie's statistics for this server"
    )
    async def stats(self, interaction: discord.Interaction):
        """View Jamie's stats for the server."""
        db = self.bot.db

        profiles = await db.get_all_profiles(interaction.guild_id)
        channels = await db.get_server_map(interaction.guild_id)
        total_messages = sum(p["message_count"] for p in profiles)

        # Top talkers
        top = sorted(profiles, key=lambda p: p["message_count"], reverse=True)[:5]
        top_list = "\n".join(
            f"  {i+1}. **{p['display_name']}** — {p['message_count']} msgs"
            for i, p in enumerate(top)
        )

        embed = discord.Embed(
            title=f"📊 Jamie Stats — {interaction.guild.name}",
            color=0x39B7C4,
        )

        embed.add_field(
            name="Overview",
            value=(
                f"👥 Users tracked: **{len(profiles)}**\n"
                f"💬 Messages memorized: **{total_messages}**\n"
                f"🗺️ Channels mapped: **{len(channels)}**\n"
                f"🏠 Servers: **{len(self.bot.guilds)}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏆 Top Talkers",
            value=top_list or "No data yet",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
