"""
ChatCog — Handles Jamie's conversations.
- Dedicated channel: Jamie responds to every message
- @mention: Jamie responds when pinged in other channels
- LLM-powered responses with user context and conversation memory
- All talk output is sent as Discord embeds
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timezone

from cogs.format_utils import send_jamie_embeds

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
        """Respond to a message in Jamie's dedicated channel (embed)."""
        async with message.channel.typing():
            db = self.bot.db
            llm = self.bot.llm

            user_context = await db.build_user_context(message.author.id, message.guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=20)

            response = await llm.generate_response(
                user_message=message.content,
                user_context=user_context,
                conversation_context=conversation_context,
                is_mention=False,
            )

            response = response.strip()
            await send_jamie_embeds(
                message.channel,
                response,
                title="🔥 Jamie",
                footer=f"to {message.author.display_name}",
            )

    # ── @mention response ──────────────────────────────────────────

    async def _respond_to_mention(self, message: discord.Message):
        """Respond when @mentioned in a side channel (embed)."""
        async with message.channel.typing():
            db = self.bot.db
            llm = self.bot.llm

            content = message.content
            for mention in message.mentions:
                if mention.id == self.bot.user.id:
                    content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
            content = content.strip()

            if not content:
                content = "Hey."

            user_context = await db.build_user_context(message.author.id, message.guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=10)

            response = await llm.generate_response(
                user_message=content,
                user_context=user_context,
                conversation_context=conversation_context,
                is_mention=True,
            )

            response = response.strip()
            await send_jamie_embeds(
                message.channel,
                response,
                title="🔥 Jamie",
                reply_to=message,
                footer=f"reply to {message.author.display_name}",
            )

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
        from cogs.format_utils import jamie_embed, split_for_embed

        chunks = split_for_embed(response, 3900)
        for i, chunk in enumerate(chunks):
            emb = jamie_embed(
                chunk,
                title="🔥 Jamie" if i == 0 else None,
                footer=f"talk · {interaction.user.display_name}" if i == len(chunks) - 1 else None,
            )
            await interaction.followup.send(embed=emb)

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
        from cogs.format_utils import jamie_embed, split_for_embed

        chunks = split_for_embed(response, 3900)
        for i, chunk in enumerate(chunks):
            emb = jamie_embed(
                chunk,
                title="🔥 Jamie" if i == 0 else None,
                footer=f"ask · {interaction.user.display_name}" if i == len(chunks) - 1 else None,
            )
            await interaction.followup.send(embed=emb)

    # ── /rant — long + / - monologue ──────────────────────────────

    @discord.app_commands.command(
        name="rant",
        description="Jamie goes on a long rant about a topic (+ praise or - roast)",
    )
    @discord.app_commands.describe(
        topic="What Jamie should rant about",
        polarity="+ for positive / praise, - for negative / roast",
    )
    @discord.app_commands.choices(
        polarity=[
            discord.app_commands.Choice(name="+ positive", value="+"),
            discord.app_commands.Choice(name="- negative", value="-"),
        ]
    )
    async def rant(
        self,
        interaction: discord.Interaction,
        topic: str,
        polarity: discord.app_commands.Choice[str],
    ):
        """Long first-person rant, up to 4000 characters, split across messages."""
        llm = self.bot.llm
        if not llm:
            await interaction.response.send_message(
                "LLM not ready yet.", ephemeral=True
            )
            return

        topic = (topic or "").strip()
        if not topic:
            await interaction.response.send_message(
                "Give me a topic to rant about.", ephemeral=True
            )
            return
        if len(topic) > 200:
            topic = topic[:200]

        pol = polarity.value if polarity else "+"
        await interaction.response.defer(thinking=True)

        try:
            text = await llm.generate_rant(topic, pol)
        except Exception as e:
            log.exception("Rant failed")
            await interaction.followup.send(f"*[Rant failed: {e}]*")
            return

        text = (text or "").strip()
        if not text:
            await interaction.followup.send("*[Empty rant — try again]*")
            return

        # Cap at 4000 chars total
        if len(text) > 4000:
            text = text[:3997].rstrip() + "..."

        from cogs.format_utils import jamie_embed, split_for_embed

        title = f"🔥 Rant {'+' if pol == '+' else '−'} · {topic}"[:256]
        chunks = split_for_embed(text, 3900)
        for i, chunk in enumerate(chunks):
            emb = jamie_embed(
                chunk,
                title=title if i == 0 else None,
                footer=f"rant · {interaction.user.display_name}" if i == len(chunks) - 1 else f"({i + 1}/{len(chunks)})",
            )
            await interaction.followup.send(embed=emb)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
