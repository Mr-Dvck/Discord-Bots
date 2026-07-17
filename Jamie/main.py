"""
Jamie Discord Bot — Main entry point
A sentient Discord bot that memorizes users, maps servers, and talks back.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load .env from the Jamie directory
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

# Also try loading from the shared bots.env
BOTS_ENV = Path(__file__).parent.parent.parent / "envs" / "bots.env"
if BOTS_ENV.exists():
    load_dotenv(BOTS_ENV, override=False)

# ── Logging ────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jamie")

# ── Intents ────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True
intents.typing = True
intents.presences = False


class JamieBot(commands.Bot):
    """Custom Bot class with shared database and LLM references."""

    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=intents,
            application_id=os.getenv("JAMIE_APP_ID"),
        )
        self.db = None
        self.llm = None
        self.image_gen = None

    async def setup_hook(self):
        """Initialize database, LLM, image generator, and load cogs."""
        from db.database import JamieDatabase
        from llm.client import LLMClient
        from image.generator import ImageGenerator

        # Initialize shared services
        self.db = JamieDatabase()
        await self.db.connect()
        log.info("Database connected")

        self.llm = LLMClient()
        await self.llm.start()
        log.info("LLM client started (model: %s)", self.llm.model)

        self.image_gen = ImageGenerator()
        await self.image_gen.start()
        log.info("Image generator started")

        # Load cogs
        cogs_dir = Path(__file__).parent / "cogs"
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue
            ext = f"cogs.{cog_file.stem}"
            try:
                await self.load_extension(ext)
                log.info("Loaded cog: %s", ext)
            except Exception as e:
                log.error("Failed to load cog %s: %s", ext, e)

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            log.info("Synced %d slash commands", len(synced))
        except Exception as e:
            log.error("Failed to sync commands: %s", e)

    async def on_ready(self):
        """Bot is connected and ready."""
        log.info("════════════════════════════════════════")
        log.info("  JAMIE IS ONLINE")
        log.info("  Guilds: %d", len(self.guilds))
        log.info("  Users:  %d", sum(g.member_count or 0 for g in self.guilds))
        log.info("════════════════════════════════════════")

        # Set presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="everything 👁️"
            ),
            status=discord.Status.online,
        )

        # Cartograph any guilds that aren't set up yet
        for guild in self.guilds:
            if not await self.db.is_setup(guild.id):
                log.info("Guild %s not set up — waiting for /setup", guild.name)

    async def on_guild_join(self, guild: discord.Guild):
        """Handle joining a new guild."""
        log.info("Joined new guild: %s (%d)", guild.name, guild.id)

    async def close(self):
        """Clean shutdown."""
        log.info("Shutting down Jamie...")
        if self.db:
            await self.db.close()
        if self.llm:
            await self.llm.close()
        if self.image_gen:
            await self.image_gen.close()
        await super().close()


# ── Entry Point ─────────────────────────────────────────────────────

def main():
    token = os.getenv("DISCORD_BOT_TOKEN_JAMIE")
    if not token:
        log.critical("DISCORD_BOT_TOKEN_JAMIE not found in environment!")
        sys.exit(1)

    bot = JamieBot()

    async def runner():
        try:
            async with bot:
                await bot.start(token)
        except KeyboardInterrupt:
            log.info("Keyboard interrupt — shutting down")
        finally:
            await bot.close()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
