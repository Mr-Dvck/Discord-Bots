"""
OnboardingCog — Handles user onboarding with personality analysis.
When a user joins the server, Jamie DMs them with an onboarding link.
Completing onboarding grants the "All Access Pass" role and stores personality data.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("jamie.onboarding")

# Role name for onboarding completion
ALL_ACCESS_ROLE_NAME = "Pond Pass"


class OnboardingCog(commands.Cog):
    """Onboarding system for new server members."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending_onboarding: dict[int, dict] = {}

    # ── Slash Commands ───────────────────────────────────────────────

    @app_commands.command(name="apply", description="Start the onboarding process with Jamie")
    @app_commands.describe(channel="Optional: Specify a channel to send the onboarding message to")
    async def apply(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Start the onboarding process."""
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None

        if not guild_id:
            await interaction.followup.send(
                "❌ This command can only be used within a server.",
                ephemeral=True
            )
            return

        # Check if already completed
        existing = await self.bot.db.get_onboarding_status(user_id, guild_id)
        if existing and existing.get("status") == "completed":
            await interaction.followup.send(
                "✅ You've already completed the onboarding process!",
                ephemeral=True
            )
            return

        # Store pending onboarding
        self._pending_onboarding[user_id] = {
            "guild_id": guild_id,
            "channel_id": (channel or interaction.channel).id if channel else interaction.channel.id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "step": 0
        }

        # Send onboarding message
        embed = discord.Embed(
            title="📝 Onboarding with Jamie",
            description=f"Hi {interaction.user.name}! I'm Jamie, the server's AI companion. I'd like to learn more about you.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="What This Is",
            value="This is a quick onboarding process where I'll ask you some questions. \n\n"
                  "The questions may seem standard, but they help me build a deep psychological profile of you. "
                  "This allows me to better understand and interact with you.",
            inline=False
        )
        embed.add_field(
            name="What You'll Get",
            value="✅ **All Access Pass** role - grants access to secret channels\n"
                  "✅ **Personalized interactions** - I'll remember your preferences\n"
                  "✅ **Admin visibility** - server admins can view your onboarding results",
            inline=False
        )
        embed.set_footer(text="Click 'Start' to begin, or 'Cancel' to stop.")

        view = discord.ui.View()
        start_button = discord.ui.Button(
            label="🚀 Start Onboarding",
            style=discord.ButtonStyle.primary,
            emoji="🚀"
        )
        cancel_button = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )

        async def start_callback(btn_interaction: discord.Interaction):
            await btn_interaction.response.defer(ephemeral=True)
            await self._start_onboarding_flow(btn_interaction)

        async def cancel_callback(btn_interaction: discord.Interaction):
            await btn_interaction.response.edit_message(
                content="❌ Onboarding cancelled. You can run `/apply` again anytime.",
                embed=None,
                view=None
            )

        start_button.callback = start_callback
        cancel_button.callback = cancel_callback
        view.add_item(start_button)
        view.add_item(cancel_button)

        target_channel = channel or interaction.channel
        await target_channel.send(embed=embed, view=view)
        await interaction.followup.send(
            f"✅ Onboarding message sent to {target_channel.mention}",
            ephemeral=True
        )

    # ── DM Handler ───────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle DM messages for onboarding flow."""
        if message.author.bot:
            return

        # Check if this is a DM
        if not isinstance(message.channel, discord.DMChannel):
            return

        user_id = message.author.id
        if user_id not in self._pending_onboarding:
            return

        # Check if user is in a server we share
        user_in_guild = False
        guild_id = None
        for guild in self.bot.guilds:
            try:
                member = await guild.fetch_member(user_id)
                if member:
                    user_in_guild = True
                    guild_id = guild.id
                    break
            except discord.NotFound:
                continue

        if not user_in_guild or not guild_id:
            return

        # Check if onboarding is in progress
        if user_id not in self._pending_onboarding:
            return

        pending = self._pending_onboarding[user_id]
        if pending.get("guild_id") != guild_id:
            return

        # Process the message as onboarding response
        await self._process_onboarding_response(message, pending)

    async def _start_onboarding_flow(self, interaction: discord.Interaction):
        """Start the onboarding flow in DMs."""
        user = interaction.user
        guild_id = self._pending_onboarding.get(user.id, {}).get("guild_id")

        if not guild_id:
            await interaction.followup.send(
                "❌ Could not find your onboarding session. Please run `/apply` again.",
                ephemeral=True
            )
            return

        # Create or find the DM channel
        dm_channel = user.dm_channel
        if not dm_channel:
            dm_channel = await user.create_dm()

        # Send initial questions
        embed = discord.Embed(
            title="👋 Let's Get Started!",
            description="I'll ask you a few questions. Be honest - this helps me understand you better!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Question 1 of 5",
            value="What's your name? (You can use a nickname if you prefer)",
            inline=False
        )
        embed.set_footer(text="Type your answer in this chat.")

        await dm_channel.send(embed=embed)

        # Update step
        self._pending_onboarding[user.id]["step"] = 1
        self._pending_onboarding[user.id]["answers"] = {"name": ""}

    async def _process_onboarding_response(self, message: discord.Message, pending: dict):
        """Process a user's onboarding response."""
        user_id = message.author.id
        guild_id = pending.get("guild_id")
        step = pending.get("step", 0)
        answers = pending.get("answers", {})

        # Store the answer
        answers[f"step_{step}"] = message.content

        # Determine next step
        if step == 1:
            # Name collected, ask about interests
            embed = discord.Embed(
                title="Nice to meet you!",
                description=f"I'll remember that your name is {message.content}.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Question 2 of 5",
                value="What are some of your favorite hobbies or interests?",
                inline=False
            )
            embed.set_footer(text="Type your answer in this chat.")

            await message.channel.send(embed=embed)
            self._pending_onboarding[user_id]["step"] = 2
            self._pending_onboarding[user_id]["answers"] = answers

        elif step == 2:
            # Interests collected, ask about personality
            embed = discord.Embed(
                title="Interesting!",
                description=f"I'll remember your interests include: {message.content}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Question 3 of 5",
                value="If you could describe yourself in 3 words, what would they be?",
                inline=False
            )
            embed.set_footer(text="Type your answer in this chat.")

            await message.channel.send(embed=embed)
            self._pending_onboarding[user_id]["step"] = 3
            self._pending_onboarding[user_id]["answers"] = answers

        elif step == 3:
            # Personality traits collected, ask about preferences
            embed = discord.Embed(
                title="Great insights!",
                description=f"Three words: {message.content}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Question 4 of 5",
                value="What kind of server activities or events do you enjoy most?",
                inline=False
            )
            embed.set_footer(text="Type your answer in this chat.")

            await message.channel.send(embed=embed)
            self._pending_onboarding[user_id]["step"] = 4
            self._pending_onboarding[user_id]["answers"] = answers

        elif step == 4:
            # Final question, then analyze and complete
            embed = discord.Embed(
                title="Almost done!",
                description=f"I'll remember you enjoy: {message.content}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Question 5 of 5",
                value="Is there anything else you'd like me to know about you?",
                inline=False
            )
            embed.set_footer(text="Type your answer in this chat (or type 'skip' to continue).")

            await message.channel.send(embed=embed)
            self._pending_onboarding[user_id]["step"] = 5
            self._pending_onboarding[user_id]["answers"] = answers

        elif step == 5:
            # Final answer collected - analyze and complete
            all_answers = "\n".join([
                f"Name: {answers.get('step_1', 'Not provided')}",
                f"Interests: {answers.get('step_2', 'Not provided')}",
                f"Personality: {answers.get('step_3', 'Not provided')}",
                f"Preferences: {answers.get('step_4', 'Not provided')}",
                f"Additional: {answers.get('step_5', 'Not provided')}"
            ])

            # Analyze with LLM
            await message.channel.send("🧠 Analyzing your responses...")

            try:
                analysis = await self.bot.llm.analyze_user_personality([all_answers])
                personality_summary = analysis.get("summary", "No summary available")
                interests = analysis.get("interests", "No interests identified")

                # Complete onboarding
                await self.bot.db.complete_onboarding(
                    user_id=user_id,
                    guild_id=guild_id,
                    personality_summary=personality_summary,
                    interests=interests
                )

                # Update user profile
                profile = await self.bot.db.get_user_profile(user_id, guild_id)
                if profile:
                    await self.bot.db.update_user_personality(
                        user_id, guild_id, personality_summary, interests
                    )

                # Grant role
                await self._grant_all_access_role(user_id, guild_id)

                # Send completion message
                embed = discord.Embed(
                    title="🎉 Onboarding Complete!",
                    description="You've successfully completed the onboarding process!",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="What You Got",
                    value="✅ **All Access Pass** role granted\n"
                          "✅ Personality profile created\n"
                          "✅ Admins can view your results",
                    inline=False
                )
                embed.add_field(
                    name="Your Profile Summary",
                    value=f"> {personality_summary[:500]}",
                    inline=False
                )
                embed.set_footer(text="Welcome to the server!")

                await message.channel.send(embed=embed)

                # Log to admin channel
                await self._log_completion_to_admins(user_id, guild_id, personality_summary, interests)

                # Clean up
                if user_id in self._pending_onboarding:
                    del self._pending_onboarding[user_id]

            except Exception as e:
                log.error("Onboarding analysis failed for %d: %s", user_id, e)
                await message.channel.send(
                    "❌ An error occurred while processing your responses. Please try again later."
                )

    async def _grant_all_access_role(self, user_id: int, guild_id: int):
        """Grant the All Access Pass role to a user."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            # Find the role
            role = discord.utils.get(guild.roles, name=ALL_ACCESS_ROLE_NAME)
            if not role:
                # Create the role if it doesn't exist
                role = await guild.create_role(
                    name=ALL_ACCESS_ROLE_NAME,
                    color=discord.Color.purple(),
                    reason="Created for onboarding system"
                )

            # Get member
            member = await guild.fetch_member(user_id)
            if member:
                await member.add_roles(role, reason="Completed onboarding")
                log.info("Granted %s role to user %d in guild %d", ALL_ACCESS_ROLE_NAME, user_id, guild_id)
        except Exception as e:
            log.error("Failed to grant role to user %d: %s", user_id, e)

    async def _log_completion_to_admins(self, user_id: int, guild_id: int, personality: str, interests: str):
        """Log onboarding completion to a designated admin channel."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return

            # Find admin log channel (look for common names)
            admin_channel = None
            for channel_name in ["admin-log", "mod-log", "onboarding-logs", "logs"]:
                admin_channel = discord.utils.get(guild.text_channels, name=channel_name)
                if admin_channel:
                    break

            if not admin_channel:
                return

            # Get user info
            try:
                member = await guild.fetch_member(user_id)
                user_info = f"{member.mention} (`{member.name}#{member.discriminator}`)"
            except:
                user_info = f"User ID: {user_id}"

            embed = discord.Embed(
                title="📝 Onboarding Complete",
                description=f"{user_info} has completed the onboarding process!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Personality Summary",
                value=f"> {personality[:1000]}",
                inline=False
            )
            embed.add_field(
                name="Interests",
                value=f"> {interests[:500]}",
                inline=False
            )
            embed.set_footer(text=f"User ID: {user_id} | Guild: {guild.name}")

            await admin_channel.send(embed=embed)
            log.info("Logged onboarding completion for user %d", user_id)

        except Exception as e:
            log.error("Failed to log onboarding completion: %s", e)


async def setup(bot: commands.Bot):
    await bot.add_cog(OnboardingCog(bot))
