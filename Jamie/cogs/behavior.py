"""
BehaviorCog — Jamie's behavior learning and persona generation system.
Observes user conversations, logs patterns anonymously, and generates
personas based on learned behaviors. Creates a "schizophrenic AI brain"
from conversation patterns.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
import random
from datetime import datetime, timezone

log = logging.getLogger("jamie.behavior")


class BehaviorCog(commands.Cog):
    """Behavior learning and persona generation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Webhook cache for posting as generated personas
        self._webhook_cache: dict[int, discord.Webhook] = {}

    # ── on_message — behavior observation ─────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Observe and log user behavior patterns."""
        if message.author.bot or not message.guild:
            return

        db = self.bot.db
        guild_id = message.guild.id

        # Only log if we have a notes log channel configured
        notes_channel_id = await db.get_notes_log_channel(guild_id)
        if not notes_channel_id:
            return

        # Analyze the message for behavior patterns
        behavior_tags = self._analyze_behavior(message.content)
        sentiment_score = self._analyze_sentiment(message.content)

        # Log the behavior
        await db.log_behavior(
            guild_id=guild_id,
            user_id=message.author.id,
            message_content=message.content,
            behavior_tags=behavior_tags,
            sentiment_score=sentiment_score,
        )

        # Periodically generate new personas (every 50 logged messages)
        patterns = await db.get_behavior_patterns(guild_id, limit=1)
        if len(patterns) > 0 and len(patterns) % 50 == 0:
            await self._generate_new_persona(guild_id)

    # ── behavior analysis helpers ─────────────────────────────────────

    def _analyze_behavior(self, content: str) -> list[str]:
        """Extract behavior tags from message content."""
        tags = []
        content_lower = content.lower()

        # Communication style
        if any(word in content_lower for word in ["lol", "lmao", "haha", "😂", "😄"]):
            tags.append("humorous")
        if any(word in content_lower for word in ["wtf", "fuck", "shit", "damn", "hell"]):
            tags.append("profane")
        if any(word in content_lower for word in ["please", "thank", "thanks", "appreciate"]):
            tags.append("polite")
        if any(word in content_lower for word in ["bro", "dude", "man", "fam"]):
            tags.append("casual")
        if any(word in content_lower for word in ["literally", "actually", "basically"]):
            tags.append("explanatory")

        # Emotional state
        if any(word in content_lower for word in ["sad", "depressed", "hate", "angry"]):
            tags.append("negative")
        if any(word in content_lower for word in ["happy", "love", "awesome", "great"]):
            tags.append("positive")
        if any(word in content_lower for word in ["anxious", "worried", "stressed"]):
            tags.append("anxious")
        if any(word in content_lower for word in ["chill", "relaxed", "calm"]):
            tags.append("calm")

        # Topic interests
        if any(word in content_lower for word in ["game", "gaming", "play", "fps"]):
            tags.append("gaming")
        if any(word in content_lower for word in ["music", "song", "album", "track"]):
            tags.append("music")
        if any(word in content_lower for word in ["code", "programming", "dev", "debug"]):
            tags.append("tech")
        if any(word in content_lower for word in ["movie", "film", "show", "series"]):
            tags.append("entertainment")

        # Interaction patterns
        if "?" in content and content.count("?") > 1:
            tags.append("inquisitive")
        if content.count("!") > 2:
            tags.append("excitable")
        if len(content) > 200:
            tags.append("verbose")
        if len(content) < 20:
            tags.append("terse")

        # Slang/meme patterns
        if any(word in content_lower for word in ["based", "cringe", "pog", "yeet"]):
            tags.append("meme_savvy")
        if any(word in content_lower for word in ["no cap", "fr", "ngl", "tbh"]):
            tags.append("gen_z_slang")

        return tags[:5]  # Limit to top 5 tags

    def _analyze_sentiment(self, content: str) -> float:
        """Simple sentiment analysis (-1.0 to 1.0)."""
        content_lower = content.lower()

        positive_words = ["love", "awesome", "great", "amazing", "excellent", "happy", "good", "best", "perfect", "wonderful", "fantastic", "brilliant", "lol", "lmao", "😂", "😄", "😊", "👍", "💯"]
        negative_words = ["hate", "terrible", "awful", "bad", "worst", "sad", "angry", "mad", "annoying", "frustrating", "disappointed", "sucks", "trash", "garbage", "😢", "😡", "👎", "💀"]

        pos_count = sum(1 for word in positive_words if word in content_lower)
        neg_count = sum(1 for word in negative_words if word in content_lower)

        if pos_count + neg_count == 0:
            return 0.0

        return (pos_count - neg_count) / (pos_count + neg_count)

    # ── persona generation ─────────────────────────────────────────────

    async def _generate_new_persona(self, guild_id: int):
        """Generate a new persona from observed behavior patterns."""
        db = self.bot.db
        llm = self.bot.llm

        if not llm:
            log.warning("LLM not available for persona generation")
            return

        # Get recent behavior patterns
        patterns = await db.get_behavior_patterns(guild_id, limit=100)
        if len(patterns) < 20:
            return  # Not enough data yet

        # Analyze patterns for persona creation
        all_tags = []
        sentiments = []
        message_samples = []

        for pattern in patterns[:50]:  # Use last 50 messages
            all_tags.extend(pattern["behavior_tags"])
            sentiments.append(pattern["sentiment_score"])
            if len(message_samples) < 10:
                message_samples.append(pattern["message_content"][:200])

        # Count tag frequencies
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        # Generate persona with LLM
        try:
            prompt = f"""
Create a Discord persona based on these observed behavior patterns:

TOP BEHAVIORS: {', '.join([f'{tag} ({count}x)' for tag, count in top_tags])}
AVERAGE SENTIMENT: {avg_sentiment:.2f} (-1.0 = very negative, 1.0 = very positive)
SAMPLE MESSAGES:
{chr(10).join(f'- {msg}' for msg in message_samples[:5])}

Generate a persona with:
1. A creative name (not real names, more like archetypes)
2. A personality description that embodies these behaviors
3. A hex color that matches the vibe (0xRRGGBB format)

Respond in JSON format:
{{
  "name": "Persona Name",
  "personality": "Detailed personality description...",
  "color": "0xRRGGBB",
  "explanation": "Brief explanation of how this persona reflects the observed patterns"
}}
"""

            response = await llm.chat([{"role": "user", "content": prompt}])
            
            # Parse JSON response
            try:
                persona_data = json.loads(response.strip())
                name = persona_data.get("name", "Unknown")
                personality = persona_data.get("personality", "A mysterious persona")
                color_str = persona_data.get("color", "0x39B7C4")
                explanation = persona_data.get("explanation", "")

                # Parse color
                try:
                    color = int(color_str.replace("#", "").replace("0x", ""), 16)
                except:
                    color = 0x39B7C4

                # Calculate confidence based on data quality
                confidence = min(len(patterns) / 100.0, 1.0) * (1.0 - abs(avg_sentiment) * 0.2)

                # Create the persona
                persona_id = await db.create_generated_persona(
                    guild_id=guild_id,
                    name=name,
                    personality=personality,
                    source_patterns={
                        "top_tags": top_tags,
                        "avg_sentiment": avg_sentiment,
                        "message_count": len(patterns),
                        "confidence_factors": {
                            "data_volume": len(patterns) / 100.0,
                            "sentiment_consistency": 1.0 - abs(avg_sentiment) * 0.2,
                            "tag_diversity": len(tag_counts) / 20.0
                        },
                        "explanation": explanation
                    },
                    confidence_score=confidence,
                    color=color,
                )

                log.info(f"Generated new persona '{name}' (ID: {persona_id}) for guild {guild_id}")

                # Post to brain channel if configured
                await self._announce_new_persona(guild_id, persona_id)

            except json.JSONDecodeError:
                log.error("Failed to parse persona JSON response")

        except Exception as e:
            log.exception("Failed to generate persona")

    async def _announce_new_persona(self, guild_id: int, persona_id: int):
        """Announce a new generated persona to the brain channel."""
        db = self.bot.db
        brain_channel_id = await db.get_brain_channel(guild_id)
        
        if not brain_channel_id:
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = guild.get_channel(brain_channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        # Get the persona details
        personas = await db.get_generated_personas(guild_id)
        persona = next((p for p in personas if p["id"] == persona_id), None)
        
        if not persona:
            return

        # Create announcement embed
        embed = discord.Embed(
            title=f"🧠 New Persona Emerged: {persona['name']}",
            description=persona["personality"][:500] + "..." if len(persona["personality"]) > 500 else persona["personality"],
            color=persona["color"],
        )

        # Add pattern analysis
        patterns = persona["source_patterns"]
        top_tags = patterns.get("top_tags", [])[:5]
        if top_tags:
            embed.add_field(
                name="Observed Behaviors",
                value=", ".join([f"{tag} ({count}x)" for tag, count in top_tags]),
                inline=False,
            )

        embed.add_field(
            name="Confidence Score",
            value=f"{patterns.get('confidence_factors', {}).get('data_volume', 0):.1%}",
            inline=True,
        )

        embed.add_field(
            name="Based On",
            value=f"{patterns.get('message_count', 0)} messages",
            inline=True,
        )

        if patterns.get("explanation"):
            embed.add_field(
                name="Analysis",
                value=patterns["explanation"][:300],
                inline=False,
            )

        embed.set_footer(text=f"Persona ID: {persona_id} • Generated from user behavior patterns")
        embed.timestamp = datetime.now(timezone.utc)

        try:
            await channel.send(embed=embed)
        except Exception as e:
            log.exception(f"Failed to announce persona to brain channel {brain_channel_id}")

    # ── commands ─────────────────────────────────────────────────────

    @app_commands.command(name="behavior-setup", description="Configure behavior learning channels")
    @app_commands.describe(
        notes_log="Channel for anonymous behavior logging",
        brain="Channel for posting generated personas (ID: 1526815578361172120)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def behavior_setup(
        self,
        interaction: discord.Interaction,
        notes_log: discord.TextChannel,
        brain: discord.TextChannel,
    ):
        """Set up the behavior learning system."""
        db = self.bot.db
        guild_id = interaction.guild_id

        await db.set_notes_log_channel(guild_id, notes_log.id)
        await db.set_brain_channel(guild_id, brain.id)

        embed = discord.Embed(
            title="🧠 Behavior Learning Configured",
            description=(
                f"**Notes Log Channel:** {notes_log.mention}\n"
                f"**Brain Channel:** {brain.mention}\n\n"
                "I'll now:\n"
                "• Anonymously log conversation patterns to the notes channel\n"
                "• Generate personas from observed behaviors\n"
                "• Post new personas to the brain channel"
            ),
            color=0x39B7C4,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Send initial message to notes log
        try:
            await notes_log.send(
                embed=discord.Embed(
                    title="📝 Behavior Logging Started",
                    description="I'm now anonymously logging conversation patterns for persona generation.",
                    color=0x39B7C4,
                )
            )
        except Exception:
            pass

    @app_commands.command(name="generate-persona", description="Manually generate a new persona from current data")
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_persona(self, interaction: discord.Interaction):
        """Manually trigger persona generation."""
        await interaction.response.defer(thinking=True)
        
        await self._generate_new_persona(interaction.guild_id)
        
        await interaction.followup.send(
            "🧠 Persona generation triggered. Check the brain channel for results.",
            ephemeral=True,
        )

    @app_commands.command(name="personas", description="List all generated personas")
    async def list_personas(self, interaction: discord.Interaction):
        """Show all generated personas."""
        db = self.bot.db
        personas = await db.get_generated_personas(interaction.guild_id)
        active = await db.get_active_generated_persona(interaction.guild_id)

        if not personas:
            await interaction.response.send_message(
                "No personas generated yet. Configure behavior learning with `/behavior-setup`.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="🧠 Generated Personas",
            description="Personas created from observed user behavior patterns",
            color=0x39B7C4,
        )

        for persona in personas[:10]:  # Show max 10
            status = "🔹 ACTIVE" if active and active["id"] == persona["id"] else ""
            confidence = persona.get("confidence_score", 0.0)
            embed.add_field(
                name=f"{persona['name']} {status}",
                value=f"Confidence: {confidence:.1%}\nCreated: {persona.get('created_at', 'Unknown')}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="switch-persona", description="Switch to a generated persona")
    @app_commands.describe(name="Name of the persona to activate")
    async def switch_persona(self, interaction: discord.Interaction, name: str):
        """Switch to a specific generated persona."""
        db = self.bot.db
        personas = await db.get_generated_personas(interaction.guild_id)
        
        persona = next((p for p in personas if p["name"].lower() == name.lower()), None)
        if not persona:
            await interaction.response.send_message(
                f"Persona '{name}' not found. Use `/personas` to see available personas.",
                ephemeral=True,
            )
            return

        await db.set_active_generated_persona(interaction.guild_id, persona["id"])

        embed = discord.Embed(
            title=f"🎭 Switched to {persona['name']}",
            description=persona["personality"][:300] + "..." if len(persona["personality"]) > 300 else persona["personality"],
            color=persona["color"],
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clear-persona", description="Return to default Jamie")
    async def clear_persona(self, interaction: discord.Interaction):
        """Clear active persona and return to default Jamie."""
        db = self.bot.db
        await db.clear_active_persona(interaction.guild_id)

        embed = discord.Embed(
            title="🔥 Back to Jamie",
            description="Returned to default Jamie persona.",
            color=0x39B7C4,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── webhook helper for posting as personas ───────────────────────

    async def _get_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """Get or create a webhook for the channel."""
        if channel.id in self._webhook_cache:
            wh = self._webhook_cache[channel.id]
            try:
                await self.bot.fetch_webhook(wh.id)
                return wh
            except discord.NotFound:
                del self._webhook_cache[channel.id]

        webhooks = await channel.webhooks()
        for wh in webhooks:
            if wh.user and wh.user.id == self.bot.user.id:
                self._webhook_cache[channel.id] = wh
                return wh

        webhook = await channel.create_webhook(name="Jamie Personas")
        self._webhook_cache[channel.id] = webhook
        return webhook


async def setup(bot: commands.Bot):
    await bot.add_cog(BehaviorCog(bot))