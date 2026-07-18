"""
MusicCog — Jamie's VC and music control system.
Can join empty voice channels, summon Tempo, and manage playlists.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import asyncio
import re
from datetime import datetime, timezone

log = logging.getLogger("jamie.music")


class MusicCog(commands.Cog):
    """Voice channel and music management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_connections: dict[int, discord.VoiceClient] = {}
        self.tempo_user_id = None  # Will be set when Tempo is found

    # ── VC Join/Leave Commands ───────────────────────────────────────

    @app_commands.command(name="join", description="Join a voice channel")
    @app_commands.describe(channel="Voice channel to join")
    async def join_vc(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Join a voice channel."""
        if interaction.user.voice is None and channel is None:
            await interaction.response.send_message(
                "You must be in a voice channel or specify one to join.",
                ephemeral=True,
            )
            return

        target_channel = channel or interaction.user.voice.channel
        if not target_channel:
            await interaction.response.send_message(
                "Could not find a voice channel to join.",
                ephemeral=True,
            )
            return

        # Check if already connected to this guild
        if interaction.guild.id in self.voice_connections:
            await interaction.response.send_message(
                "I'm already connected to a voice channel in this server.",
                ephemeral=True,
            )
            return

        # Check permissions - only require connect, not speak (Jamie can join to take up space)
        permissions = target_channel.permissions_for(interaction.guild.me)
        if not permissions.connect:
            await interaction.response.send_message(
                f"I don't have permission to connect to {target_channel.mention}.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            voice_client = await target_channel.connect()
            self.voice_connections[interaction.guild.id] = voice_client
            # No message sent - Jamie joins silently
            # Don't send any response to avoid "Cannot send an empty message" error
            
        except Exception as e:
            log.exception("Failed to join voice channel")
            await interaction.followup.send(
                f"Failed to join voice channel: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="leave", description="Leave the current voice channel")
    async def leave_vc(self, interaction: discord.Interaction):
        """Leave the current voice channel."""
        if interaction.guild.id not in self.voice_connections:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            voice_client = self.voice_connections[interaction.guild.id]
            await voice_client.disconnect()
            del self.voice_connections[interaction.guild.id]
            
            await interaction.followup.send("👋 Left voice channel")
            
        except Exception as e:
            log.exception("Failed to leave voice channel")
            await interaction.followup.send(
                f"Failed to leave voice channel: {str(e)}",
                ephemeral=True,
            )

    # ── Tempo Integration ─────────────────────────────────────────────

    @app_commands.command(name="summon-tempo", description="Summon Tempo to the current voice channel")
    async def summon_tempo(self, interaction: discord.Interaction):
        """Summon Tempo music bot to the current voice channel."""
        if interaction.guild.id not in self.voice_connections:
            await interaction.response.send_message(
                "I need to be in a voice channel first. Use /join to connect.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Find Tempo in the server
        tempo_member = None
        for member in interaction.guild.members:
            if member.bot and "tempo" in member.name.lower():
                tempo_member = member
                self.tempo_user_id = member.id
                break

        if not tempo_member:
            await interaction.followup.send(
                "❌ Tempo not found in this server. Make sure Tempo is invited and has permissions.",
                ephemeral=True,
            )
            return

        # Get the voice channel Jamie is in
        voice_client = self.voice_connections[interaction.guild.id]
        voice_channel = voice_client.channel

        # Try to summon Tempo using common summon commands
        summon_commands = [
            f"!summon",
            f"-summon", 
            f"/summon",
            f"t!summon",
            f"tempo summon",
            f"hey tempo join",
        ]

        success = False
        for cmd in summon_commands:
            try:
                # Send the summon command in a text channel
                # Try to find a channel Tempo can read
                target_channel = interaction.channel
                if not target_channel.permissions_for(tempo_member).read_messages:
                    # Find another channel
                    for ch in interaction.guild.text_channels:
                        if ch.permissions_for(tempo_member).read_messages:
                            target_channel = ch
                            break

                await target_channel.send(cmd)
                success = True
                break
                
            except Exception:
                continue

        if success:
            embed = discord.Embed(
                title="🎵 Summoning Tempo",
                description=f"Attempting to summon {tempo_member.mention} to {voice_channel.mention}",
                color=0x39B7C4,
            )
            embed.add_field(
                name="Next Steps",
                value="Use /play <song> or /playlist <name> to start playing music",
                inline=False,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "❌ Failed to summon Tempo. Make sure Tempo has proper permissions.",
                ephemeral=True,
            )

    # ── Playlist Management ───────────────────────────────────────────

    @app_commands.command(name="playlist", description="Load a playlist in Tempo")
    @app_commands.describe(name="Playlist name or URL")
    async def load_playlist(self, interaction: discord.Interaction, name: str):
        """Load a playlist using Tempo."""
        await interaction.response.defer()

        # Check if Tempo is in the server
        if not self.tempo_user_id:
            tempo_member = None
            for member in interaction.guild.members:
                if member.bot and "tempo" in member.name.lower():
                    tempo_member = member
                    self.tempo_user_id = member.id
                    break
            
            if not tempo_member:
                await interaction.followup.send(
                    "❌ Tempo not found. Use /summon-tempo first.",
                    ephemeral=True,
                )
                return

        # Try different playlist commands
        playlist_commands = [
            f"!playlist {name}",
            f"-playlist {name}",
            f"/playlist {name}",
            f"t!playlist {name}",
            f"tempo playlist {name}",
        ]

        success = False
        for cmd in playlist_commands:
            try:
                await interaction.channel.send(cmd)
                success = True
                break
            except Exception:
                continue

        if success:
            embed = discord.Embed(
                title="🎵 Loading Playlist",
                description=f"Loading playlist: **{name}**",
                color=0x39B7C4,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "❌ Failed to load playlist. Check the playlist name and Tempo's permissions.",
                ephemeral=True,
            )

    @app_commands.command(name="play", description="Play a song using Tempo")
    @app_commands.describe(song="Song name or URL")
    async def play_song(self, interaction: discord.Interaction, song: str):
        """Play a song using Tempo."""
        await interaction.response.defer()

        # Check if Tempo is in the server
        if not self.tempo_user_id:
            tempo_member = None
            for member in interaction.guild.members:
                if member.bot and "tempo" in member.name.lower():
                    tempo_member = member
                    self.tempo_user_id = member.id
                    break
            
            if not tempo_member:
                await interaction.followup.send(
                    "❌ Tempo not found. Use /summon-tempo first.",
                    ephemeral=True,
                )
                return

        # Try different play commands
        play_commands = [
            f"!play {song}",
            f"-play {song}",
            f"/play {song}",
            f"t!play {song}",
            f"tempo play {song}",
        ]

        success = False
        for cmd in play_commands:
            try:
                await interaction.channel.send(cmd)
                success = True
                break
            except Exception:
                continue

        if success:
            embed = discord.Embed(
                title="🎵 Playing Song",
                description=f"Playing: **{song}**",
                color=0x39B7C4,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                "❌ Failed to play song. Check the song name/URL and Tempo's permissions.",
                ephemeral=True,
            )

    # ── Tempo Control Commands ───────────────────────────────────────

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause_music(self, interaction: discord.Interaction):
        """Pause music using Tempo."""
        await self._tempo_command(interaction, ["!pause", "-pause", "/pause", "t!pause", "tempo pause"], "⏸️ Paused")

    @app_commands.command(name="resume", description="Resume the current song")
    async def resume_music(self, interaction: discord.Interaction):
        """Resume music using Tempo."""
        await self._tempo_command(interaction, ["!resume", "-resume", "/resume", "t!resume", "tempo resume"], "▶️ Resumed")

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip_music(self, interaction: discord.Interaction):
        """Skip song using Tempo."""
        await self._tempo_command(interaction, ["!skip", "-skip", "/skip", "t!skip", "tempo skip"], "⏭️ Skipped")

    @app_commands.command(name="stop", description="Stop the music")
    async def stop_music(self, interaction: discord.Interaction):
        """Stop music using Tempo."""
        await self._tempo_command(interaction, ["!stop", "-stop", "/stop", "t!stop", "tempo stop"], "⏹️ Stopped")

    @app_commands.command(name="volume", description="Set the volume")
    @app_commands.describe(level="Volume level (0-100)")
    async def set_volume(self, interaction: discord.Interaction, level: int):
        """Set volume using Tempo."""
        if not 0 <= level <= 100:
            await interaction.response.send_message(
                "Volume must be between 0 and 100.",
                ephemeral=True,
            )
            return
        
        await self._tempo_command(interaction, [f"!volume {level}", f"-volume {level}", f"/volume {level}", f"t!volume {level}", f"tempo volume {level}"], f"🔊 Volume set to {level}%")

    async def _tempo_command(self, interaction: discord.Interaction, commands: list[str], success_msg: str):
        """Execute a Tempo command."""
        await interaction.response.defer()

        # Check if Tempo is in the server
        if not self.tempo_user_id:
            tempo_member = None
            for member in interaction.guild.members:
                if member.bot and "tempo" in member.name.lower():
                    tempo_member = member
                    self.tempo_user_id = member.id
                    break
            
            if not tempo_member:
                await interaction.followup.send(
                    "❌ Tempo not found. Use /summon-tempo first.",
                    ephemeral=True,
                )
                return

        # Try each command variation
        for cmd in commands:
            try:
                await interaction.channel.send(cmd)
                await interaction.followup.send(success_msg)
                return
            except Exception:
                continue

        await interaction.followup.send(
            "❌ Failed to execute command. Make sure Tempo is active and has permissions.",
            ephemeral=True,
        )

    # ── Voice State Events ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates."""
        # If Jamie is alone in a voice channel for more than 5 minutes, leave
        if member.id == self.bot.user.id and after.channel:
            await asyncio.sleep(300)  # 5 minutes
            
            # Check if still in the same channel and alone
            if after.channel and after.channel.guild.id in self.voice_connections:
                voice_client = self.voice_connections[after.channel.guild.id]
                if voice_client and voice_client.channel == after.channel:
                    # Count non-bot members
                    non_bot_members = [m for m in after.channel.members if not m.bot]
                    if len(non_bot_members) == 0:  # Only bots left
                        try:
                            await voice_client.disconnect()
                            del self.voice_connections[after.channel.guild.id]
                            log.info(f"Left empty voice channel: {after.channel.name}")
                        except Exception:
                            pass

    # ── Helper Methods ───────────────────────────────────────────────

    def get_voice_client(self, guild_id: int) -> discord.VoiceClient | None:
        """Get the voice client for a guild."""
        return self.voice_connections.get(guild_id)

    async def disconnect_all(self):
        """Disconnect from all voice channels."""
        for guild_id, voice_client in list(self.voice_connections.items()):
            try:
                await voice_client.disconnect()
            except Exception:
                pass
        self.voice_connections.clear()


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))