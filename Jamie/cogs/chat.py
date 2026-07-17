"""
ChatCog — Handles Jamie's conversations.
- Dedicated channel: Jamie responds to every message
- @mention: Jamie responds when pinged in other channels
- LLM-powered responses with user context and conversation memory
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone

log = logging.getLogger("jamie.chat")


class ChatCog(commands.Cog):
    """Jamie's conversation engine."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── on_message — route conversations ──────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle conversations in Jamie's channel and @mentions."""
        if message.author.bot or not message.guild:
            return

        db = self.bot.db
        guild_id = message.guild.id

        # Check if this guild is set up
        if not await db.is_setup(guild_id):
            return

        jamie_channel_id = await db.get_channel(guild_id)

        # Case 1: Message in Jamie's dedicated channel
        if message.channel.id == jamie_channel_id:
            if message.author.id == self.bot.user.id:
                return
            await self._respond_in_channel(message)
            return

        # Case 2: Jamie is @mentioned in another channel
        if self.bot.user in message.mentions:
            await self._respond_to_mention(message)
            return

    # ── dedicated channel response ────────────────────────────────

    async def _respond_in_channel(self, message: discord.Message):
        """Respond to a message in Jamie's dedicated channel."""
        async with message.channel.typing():
            db = self.bot.db
            llm = self.bot.llm

            # Build context
            user_context = await db.build_user_context(message.author.id, message.guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=20)

            # Generate response
            response = await llm.generate_response(
                user_message=message.content,
                user_context=user_context,
                conversation_context=conversation_context,
                is_mention=False,
            )

            # Clean up the response (remove any unwanted prefixes)
            response = response.strip()

            # Split if too long for Discord (2000 char limit)
            if len(response) > 2000:
                # Split at paragraph breaks
                chunks = []
                while len(response) > 2000:
                    split_at = response[:2000].rfind("\n\n")
                    if split_at < 500:
                        split_at = response[:2000].rfind("\n")
                    if split_at < 500:
                        split_at = 1997
                    chunks.append(response[:split_at + 1])
                    response = response[split_at + 1:]
                chunks.append(response)

                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response)

    # ── @mention response ──────────────────────────────────────────

    async def _respond_to_mention(self, message: discord.Message):
        """Respond when @mentioned in a side channel."""
        async with message.channel.typing():
            db = self.bot.db
            llm = self.bot.llm

            # Remove the @mention from the message content
            content = message.content
            for mention in message.mentions:
                if mention.id == self.bot.user.id:
                    content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
            content = content.strip()

            if not content:
                content = "Hey."

            # Build context
            user_context = await db.build_user_context(message.author.id, message.guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=10)

            # Generate response
            response = await llm.generate_response(
                user_message=content,
                user_context=user_context,
                conversation_context=conversation_context,
                is_mention=True,
            )

            response = response.strip()

            if len(response) > 2000:
                response = response[:1997] + "..."

            await message.reply(response)

    # ── /talk command — direct conversation ───────────────────────

    @discord.app_commands.command(
        name="talk",
        description="Talk to Jamie directly"
    )
    @discord.app_commands.describe(message="What you want to say to Jamie")
    async def talk(self, interaction: discord.Interaction, message: str):
        """Direct conversation command."""
        db = self.bot.db
        llm = self.bot.llm

        # Check setup
        if not await db.is_setup(interaction.guild_id):
            await interaction.response.send_message(
                "❌ I'm not set up yet. An admin needs to run `/setup` first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        user_context = await db.build_user_context(interaction.user.id, interaction.guild_id)
        conversation_context = ""

        response = await llm.generate_response(
            user_message=message,
            user_context=user_context,
            conversation_context=conversation_context,
            is_mention=False,
        )

        response = response.strip()
        if len(response) > 2000:
            response = response[:1997] + "..."

        await interaction.followup.send(response)

    # ── /ask command — ask about someone/something ────────────────

    @discord.app_commands.command(
        name="ask",
        description="Ask Jamie about a user or something that happened"
    )
    @discord.app_commands.describe(
        query="Who or what you're asking about",
        user="Specific user to ask about (optional)"
    )
    async def ask(self, interaction: discord.Interaction, query: str,
                  user: discord.Member = None):
        """Ask Jamie about a user or topic."""
        db = self.bot.db
        llm = self.bot.llm

        if not await db.is_setup(interaction.guild_id):
            await interaction.response.send_message(
                "❌ I'm not set up yet. An admin needs to run `/setup` first.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        # Build context based on query
        context_parts = []

        if user:
            user_context = await db.build_user_context(user.id, interaction.guild_id)
            context_parts.append(f"Question is about: {user.display_name}\n{user_context}")

        # Search for relevant messages
        search_results = await db.search_messages(interaction.guild_id, query, limit=10)
        if search_results:
            snippets = "\n".join(
                f"  [{m['username']} in #{m['channel_name']}]: {m['content'][:100]}"
                for m in search_results
            )
            context_parts.append(f"Related messages I remember:\n{snippets}")

        full_context = "\n\n".join(context_parts)

        prompt = f"Someone is asking: \"{query}\"\n\nContext:\n{full_context}" if full_context else query

        response = await llm.generate_response(
            user_message=prompt,
            user_context="",
            conversation_context="",
            is_mention=False,
        )

        response = response.strip()
        if len(response) > 2000:
            response = response[:1997] + "..."

        await interaction.followup.send(response)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
