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
        self.started_at = None

    async def setup_hook(self):
        """Initialize database, LLM, image generator, and load cogs."""
        from datetime import datetime, timezone

        from db.database import JamieDatabase
        from llm.client import LLMClient
        from image.generator import ImageGenerator

        self.started_at = datetime.now(timezone.utc)

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

        @self.tree.interaction_check
        async def global_interaction_check(interaction: discord.Interaction) -> bool:
            if not await self.is_owner(interaction.user):
                raise discord.app_commands.CheckFailure("Only the bot owner is authorized to use Jamie.")
            return True

        # Always reply on slash errors so Discord never shows "application did not respond"
        @self.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction,
            error: discord.app_commands.AppCommandError,
        ):
            log.exception("Slash command error: %s", error)
            msg = "Something broke running that command."
            if isinstance(error, discord.app_commands.CheckFailure):
                msg = str(error) or "You don't have permission to use that command."
            elif isinstance(error, discord.app_commands.CommandOnCooldown):
                msg = f"Slow down — try again in {error.retry_after:.1f}s."
            elif isinstance(error, discord.app_commands.CommandInvokeError):
                msg = f"Command failed: {error.original}"
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
            except Exception:
                log.exception("Failed to send error response")

        # Global slash commands only (one set — no guild copies = no duplicates).
        # Propagation can take a few minutes after first publish.
        try:
            synced = await self.tree.sync()
            names = sorted(c.name for c in synced)
            log.info("Synced %d global slash commands: %s", len(synced), ", ".join(names))
        except Exception as e:
            log.error("Failed to sync global commands: %s", e)

        self._cleared_guild_command_dups = False

    async def _clear_guild_command_duplicates(self):
        """
        Remove per-guild command copies left over from copy_global_to.
        Those stack on top of global commands and show as duplicates in Discord.
        """
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                log.info("Cleared guild command copies for %s (%s)", guild.name, guild.id)
            except Exception as e:
                log.error("Failed clearing guild commands for %s: %s", guild.id, e)

    async def on_ready(self):
        """Bot is connected and ready."""
        log.info("════════════════════════════════════════")
        log.info("  JAMIE IS ONLINE")
        log.info("  Guilds: %d", len(self.guilds))
        log.info("  Users:  %d", sum(g.member_count or 0 for g in self.guilds))
        log.info("════════════════════════════════════════")

        if not getattr(self, "_cleared_guild_command_dups", False):
            self._cleared_guild_command_dups = True
            await self._clear_guild_command_duplicates()

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

    async def on_error(self, event_method: str, *args, **kwargs):
        log.exception("Unhandled error in event %s", event_method)

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
    # bot.run keeps the process alive cleanly (no double-close with async with)
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    # File logging so detached restarts stay diagnosable
    log_path = Path(__file__).parent / "jamie-bot.err"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", "%H:%M:%S")
    )
    logging.getLogger().addHandler(fh)
    main()
