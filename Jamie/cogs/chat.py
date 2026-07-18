"""
ChatCog — Handles Jamie's conversations.
- Dedicated channel: Jamie responds to every message
- @mention: Jamie responds when pinged in other channels
- LLM-powered responses with user context and conversation memory
- All talk output is sent as Discord embeds
- Voice channel joining (minimal VC functionality)
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timezone

from cogs.format_utils import send_jamie_embeds
from llm.client import JAMIE_SYSTEM_PROMPT

log = logging.getLogger("jamie.chat")


class ChatCog(commands.Cog):
    """Jamie's conversation engine."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Webhook cache: channel_id -> discord.Webhook (avoids re-fetching every message)
        self._webhook_cache: dict[int, discord.Webhook] = {}
        # Voice connections: guild_id -> discord.VoiceClient
        self.voice_connections: dict[int, discord.VoiceClient] = {}

    # ── on_message — route conversations ──────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle conversations in Jamie's channel, @mentions, and custom characters."""
        if message.author.bot or not message.guild:
            return

        db = self.bot.db
        guild_id = message.guild.id

        # Check if this guild is set up
        if not await db.is_setup(guild_id):
            return

        # 1. Check if the message triggers any custom character prefix (shortcut: e.g. "cynthia: ")
        chars = await db.get_custom_characters(guild_id)
        content_lower = message.content.lower().strip()
        
        for char in chars:
            shortcut = char.get("shortcut", "").lower()
            if shortcut:
                prefix_colon = f"{shortcut}:"
                prefix_space = f"{shortcut} "
                if content_lower.startswith(prefix_colon) or content_lower.startswith(prefix_space):
                    prefix_len = len(prefix_colon) if content_lower.startswith(prefix_colon) else len(prefix_space)
                    prompt = message.content[prefix_len:].strip()
                    await self._respond_with_character(message, char, prompt)
                    return

        # 2. Check if a character name is explicitly mentioned in the text (outside of dedicated channel)
        jamie_channel_id = await db.get_channel(guild_id)
        if message.channel.id != jamie_channel_id:
            for char in chars:
                char_name = char.get("name", "").lower()
                if char_name and char_name in content_lower:
                    await self._respond_with_character(message, char, message.content)
                    return

        # 3. Jamie is @mentioned anywhere - respond immediately
        if self.bot.user in message.mentions:
            await self._respond_to_mention(message)
            return

        # 4. Message in Jamie's dedicated channel - always respond
        if message.channel.id == jamie_channel_id:
            if message.author.id == self.bot.user.id:
                return
            await self._respond_in_channel(message)
            return

        # 5. Jamie responds in ANY channel (omnipresent mode)
        # Rarely respond to maintain intimidating presence - only when absolutely necessary
        import random
        omnipresent_enabled = await db.get_omnipresent_mode(guild_id)
        if omnipresent_enabled:
            omnipresent_chance = await db.get_omnipresent_chance(guild_id)
            if random.random() < omnipresent_chance:
                if message.author.id != self.bot.user.id:
                    # Only respond to serious conversations or threats to server
                    content_lower = message.content.lower()
                    # Respond only to serious matters: security threats, drama, server issues
                    serious_keywords = [
                        'kick', 'ban', 'drama', 'fight', 'security', 'threat', 'problem',
                        'duck', 'owner', 'admin', 'mod', 'rule', 'vibe', 'toxic', 'spill',
                        'beef', 'conflict', 'issue', 'trouble', 'danger', 'risk'
                    ]
                    is_serious = any(keyword in content_lower for keyword in serious_keywords)
                    
                    # Don't respond to commands, very short messages, or casual chat
                    if (not message.content.startswith('/') and
                        len(message.content.strip()) > 10 and
                        is_serious):
                        await self._respond_to_mention(message)
                        return

    # ── Agent Tools List ──────────────────────────────────────────

    BOT_TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "join_voice_channel",
                "description": "Join a voice channel for music/voice activities. Jamie will join to take up space in the channel (without speaking permission).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_name": {"type": "string", "description": "Name of the voice channel to join"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "leave_voice_channel",
                "description": "Leave the current voice channel.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "summon_tempo",
                "description": "Summon Tempo music bot to the current voice channel.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "Play a song or playlist using Tempo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Song name, playlist name, or URL to play"}
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "control_music",
                "description": "Control music playback (pause, resume, skip, stop, volume).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["pause", "resume", "skip", "stop", "volume"], "description": "Music control action"},
                        "volume": {"type": "integer", "description": "Volume level 0-100 (only for volume action)"}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_channel",
                "description": "Create a text, voice, or category channel in the guild.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Channel name (spaces will be normalized)"},
                        "type": {"type": "string", "enum": ["text", "voice", "category"], "description": "Channel type"},
                        "parent_id": {"type": "string", "description": "Category ID under which to place the channel"}
                    },
                    "required": ["name", "type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_channel",
                "description": "Delete a channel from the guild.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Snowflake ID of the channel to delete"}
                    },
                    "required": ["channel_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_role",
                "description": "Create a role in the guild.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Role name"},
                        "color": {"type": "string", "description": "Hex color string like #FF0000"},
                        "hoist": {"type": "boolean", "description": "Show role members separately"}
                    },
                    "required": ["name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_role",
                "description": "Delete a role from the guild.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "description": "Role ID to delete"}
                    },
                    "required": ["role_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "assign_role",
                "description": "Assign a role to a member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"},
                        "role_id": {"type": "string", "description": "Role snowflake ID"}
                    },
                    "required": ["user_id", "role_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "remove_role",
                "description": "Remove a role from a member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"},
                        "role_id": {"type": "string", "description": "Role snowflake ID"}
                    },
                    "required": ["user_id", "role_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "kick_member",
                "description": "Kick a member from the guild.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"},
                        "reason": {"type": "string", "description": "Kick reason"}
                    },
                    "required": ["user_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ban_member",
                "description": "Ban a member from the guild.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"},
                        "reason": {"type": "string", "description": "Ban reason"}
                    },
                    "required": ["user_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "unban_member",
                "description": "Unban a member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"}
                    },
                    "required": ["user_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_nickname",
                "description": "Set a member's nickname.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"},
                        "nickname": {"type": "string", "description": "New nickname"}
                    },
                    "required": ["user_id", "nickname"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "timeout_member",
                "description": "Timeout a member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User snowflake ID"},
                        "duration": {"type": "string", "description": "e.g. 10m, 1h, 1d"},
                        "reason": {"type": "string", "description": "Timeout reason"}
                    },
                    "required": ["user_id", "duration"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_message",
                "description": "Send a message to a channel.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel_id": {"type": "string", "description": "Channel snowflake ID"},
                        "content": {"type": "string", "description": "Message content"}
                    },
                    "required": ["channel_id", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_starboard_config",
                "description": "Configure the starboard module settings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean", "description": "Enable or disable starboard"},
                        "channel_id": {"type": "string", "description": "Channel ID to post starboard embeds, or null/empty to clear"},
                        "min_stars": {"type": "integer", "description": "Minimum stars required"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_welcome_config",
                "description": "Configure the welcome join notification settings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean", "description": "Enable or disable welcome"},
                        "channel_id": {"type": "string", "description": "Channel ID to post welcome messages"},
                        "message": {"type": "string", "description": "Welcome message template"},
                        "dm_on_join": {"type": "boolean", "description": "Whether to DM the user on join"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_channels",
                "description": "List all channels in the server.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_roles",
                "description": "List all roles in the server.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_members",
                "description": "List some server members.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_member_note",
                "description": "Add a staff note about a user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Snowflake ID of the user"},
                        "content": {"type": "string", "description": "Note content to save"}
                    },
                    "required": ["user_id", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_member_notes",
                "description": "Get all staff notes taken for a user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Snowflake ID of the user"}
                    },
                    "required": ["user_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_member_note",
                "description": "Delete a staff note by its ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "note_id": {"type": "integer", "description": "Numeric ID of the note"}
                    },
                    "required": ["note_id"]
                }
            }
        }
    ]

    async def _execute_bot_tool(self, name: str, args: dict, message: discord.Message) -> dict:
        guild = message.guild
        try:
            # ── Music & Voice Tools ─────────────────────────────────────
            if name == "join_voice_channel":
                from cogs.music import MusicCog
                music_cog = self.bot.get_cog("MusicCog")
                if not music_cog:
                    return {"error": "Music system not available"}
                
                channel_name = args.get("channel_name")
                target_channel = None
                
                if channel_name:
                    # Find voice channel by name
                    for vc in guild.voice_channels:
                        if channel_name.lower() in vc.name.lower():
                            target_channel = vc
                            break
                elif message.author.voice:
                    target_channel = message.author.voice.channel
                
                if not target_channel:
                    return {"error": "No voice channel found"}
                
                voice_client = music_cog.get_voice_client(guild.id)
                if voice_client:
                    return {"error": "Already connected to a voice channel"}
                
                permissions = target_channel.permissions_for(guild.me)
                if not permissions.connect or not permissions.speak:
                    return {"error": "No permission to join/speak in voice channel"}
                
                voice_client = await target_channel.connect()
                music_cog.voice_connections[guild.id] = voice_client
                
                return {"success": f"Joined {target_channel.name}"}
            
            elif name == "leave_voice_channel":
                from cogs.music import MusicCog
                music_cog = self.bot.get_cog("MusicCog")
                if not music_cog:
                    return {"error": "Music system not available"}
                
                voice_client = music_cog.get_voice_client(guild.id)
                if not voice_client:
                    return {"error": "Not connected to any voice channel"}
                
                await voice_client.disconnect()
                if guild.id in music_cog.voice_connections:
                    del music_cog.voice_connections[guild.id]
                
                return {"success": "Left voice channel"}
            
            elif name == "summon_tempo":
                from cogs.music import MusicCog
                music_cog = self.bot.get_cog("MusicCog")
                if not music_cog:
                    return {"error": "Music system not available"}
                
                voice_client = music_cog.get_voice_client(guild.id)
                if not voice_client:
                    return {"error": "Not in a voice channel"}
                
                # Find Tempo
                tempo_member = None
                for member in guild.members:
                    if member.bot and "tempo" in member.name.lower():
                        tempo_member = member
                        music_cog.tempo_user_id = member.id
                        break
                
                if not tempo_member:
                    return {"error": "Tempo not found in server"}
                
                # Try summon commands
                summon_commands = ["!summon", "-summon", "/summon", "t!summon", "tempo summon"]
                for cmd in summon_commands:
                    try:
                        await message.channel.send(cmd)
                        return {"success": f"Summoning {tempo_member.name}"}
                    except Exception:
                        continue
                
                return {"error": "Failed to summon Tempo"}
            
            elif name == "play_music":
                from cogs.music import MusicCog
                music_cog = self.bot.get_cog("MusicCog")
                if not music_cog:
                    return {"error": "Music system not available"}
                
                query = args.get("query", "")
                if not query:
                    return {"error": "No song or playlist specified"}
                
                # Check if Tempo is available
                if not music_cog.tempo_user_id:
                    tempo_member = None
                    for member in guild.members:
                        if member.bot and "tempo" in member.name.lower():
                            tempo_member = member
                            music_cog.tempo_user_id = member.id
                            break
                    
                    if not tempo_member:
                        return {"error": "Tempo not found. Summon Tempo first"}
                
                # Try play commands
                play_commands = [f"!play {query}", f"-play {query}", f"/play {query}", f"t!play {query}", f"tempo play {query}"]
                for cmd in play_commands:
                    try:
                        await message.channel.send(cmd)
                        return {"success": f"Playing: {query}"}
                    except Exception:
                        continue
                
                return {"error": f"Failed to play: {query}"}
            
            elif name == "control_music":
                from cogs.music import MusicCog
                music_cog = self.bot.get_cog("MusicCog")
                if not music_cog:
                    return {"error": "Music system not available"}
                
                action = args.get("action", "")
                volume = args.get("volume")
                
                if not music_cog.tempo_user_id:
                    tempo_member = None
                    for member in guild.members:
                        if member.bot and "tempo" in member.name.lower():
                            tempo_member = member
                            music_cog.tempo_user_id = member.id
                            break
                    
                    if not tempo_member:
                        return {"error": "Tempo not found. Summon Tempo first"}
                
                # Build command based on action
                if action == "volume" and volume is not None:
                    cmd = f"!volume {volume}"
                elif action in ["pause", "resume", "skip", "stop"]:
                    cmd = f"!{action}"
                else:
                    return {"error": "Invalid action"}
                
                # Try command
                try:
                    await message.channel.send(cmd)
                    return {"success": f"Executed: {action}"}
                except Exception:
                    return {"error": f"Failed to execute: {action}"}
            
            # ── Original Server Management Tools ───────────────────────
            if name == "create_channel":
                ch_name = args.get("name")
                ch_type = args.get("type", "text")
                parent_id = args.get("parent_id")
                
                parent = guild.get_channel(int(parent_id)) if parent_id else None
                if ch_type == "category":
                    ch = await guild.create_category(ch_name)
                elif ch_type == "voice":
                    ch = await guild.create_voice_channel(ch_name, category=parent)
                else:
                    ch = await guild.create_text_channel(ch_name, category=parent)
                return {"success": True, "channel_id": str(ch.id), "name": ch.name}

            elif name == "delete_channel":
                channel_id = args.get("channel_id")
                ch = guild.get_channel(int(channel_id))
                if ch:
                    await ch.delete()
                    return {"success": True}
                return {"error": "Channel not found"}

            elif name == "create_role":
                r_name = args.get("name")
                color = args.get("color")
                hoist = args.get("hoist", False)
                
                from cogs._helpers import parse_hex_color
                val = parse_hex_color(color) if color else None
                c = discord.Color(val) if val is not None else discord.Color.default()
                role = await guild.create_role(name=r_name, color=c, hoist=hoist)
                return {"success": True, "role_id": str(role.id), "name": role.name}

            elif name == "delete_role":
                role_id = args.get("role_id")
                role = guild.get_role(int(role_id))
                if role:
                    await role.delete()
                    return {"success": True}
                return {"error": "Role not found"}

            elif name == "assign_role":
                user_id = args.get("user_id")
                role_id = args.get("role_id")
                
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(int(role_id))
                if member and role:
                    await member.add_roles(role)
                    return {"success": True}
                return {"error": "Member or role not found"}

            elif name == "remove_role":
                user_id = args.get("user_id")
                role_id = args.get("role_id")
                
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                role = guild.get_role(int(role_id))
                if member and role:
                    await member.remove_roles(role)
                    return {"success": True}
                return {"error": "Member or role not found"}

            elif name == "kick_member":
                user_id = args.get("user_id")
                reason = args.get("reason")
                
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                if member:
                    await member.kick(reason=reason)
                    return {"success": True}
                return {"error": "Member not found"}

            elif name == "ban_member":
                user_id = args.get("user_id")
                reason = args.get("reason")
                
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                if member:
                    await member.ban(reason=reason)
                    return {"success": True}
                return {"error": "Member not found"}

            elif name == "unban_member":
                user_id = args.get("user_id")
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    await guild.unban(user)
                    return {"success": True}
                return {"error": "User not found"}

            elif name == "set_nickname":
                user_id = args.get("user_id")
                nickname = args.get("nickname")
                
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                if member:
                    await member.edit(nick=nickname)
                    return {"success": True}
                return {"error": "Member not found"}

            elif name == "timeout_member":
                user_id = args.get("user_id")
                duration = args.get("duration")
                reason = args.get("reason")
                
                from cogs._helpers import parse_duration
                delta = parse_duration(duration)
                member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                if member and delta:
                    await member.timeout(delta, reason=reason)
                    return {"success": True}
                return {"error": "Member not found or invalid duration"}

            elif name == "send_message":
                channel_id = args.get("channel_id")
                content = args.get("content")
                
                ch = guild.get_channel(int(channel_id)) or await self.bot.fetch_channel(int(channel_id))
                if ch and isinstance(ch, discord.TextChannel):
                    await ch.send(content)
                    return {"success": True}
                return {"error": "Channel not found"}

            elif name == "set_starboard_config":
                enabled = args.get("enabled")
                ch_id = args.get("channel_id")
                min_stars = args.get("min_stars")
                
                kwargs = {}
                if enabled is not None: kwargs["enabled"] = 1 if enabled else 0
                if ch_id is not None: kwargs["channel_id"] = int(ch_id) if ch_id else None
                if min_stars is not None: kwargs["min_stars"] = int(min_stars)
                
                await self.bot.db.upsert_starboard_config(guild.id, **kwargs)
                return {"success": True}

            elif name == "set_welcome_config":
                enabled = args.get("enabled")
                ch_id = args.get("channel_id")
                message = args.get("message")
                dm_on_join = args.get("dm_on_join")
                
                kwargs = {}
                if enabled is not None: kwargs["enabled"] = 1 if enabled else 0
                if ch_id is not None: kwargs["channel_id"] = int(ch_id) if ch_id else None
                if message is not None: kwargs["message"] = message
                if dm_on_join is not None: kwargs["dm_on_join"] = 1 if dm_on_join else 0
                
                await self.bot.db.upsert_welcome_config(guild.id, **kwargs)
                return {"success": True}

            elif name == "list_channels":
                return {"success": True, "channels": [{"id": str(c.id), "name": c.name, "type": str(c.type)} for c in guild.channels]}

            elif name == "list_roles":
                return {"success": True, "roles": [{"id": str(r.id), "name": r.name} for r in guild.roles]}

            elif name == "list_members":
                return {"success": True, "members": [{"id": str(m.id), "name": str(m)} for m in guild.members[:100]]}

            elif name == "add_member_note":
                user_id = args.get("user_id")
                content = args.get("content")
                mod_id = message.author.id
                nid = await self.bot.db.add_member_note(guild.id, int(user_id), mod_id, content)
                return {"success": True, "note_id": nid}

            elif name == "get_member_notes":
                user_id = args.get("user_id")
                notes = await self.bot.db.get_member_notes(guild.id, int(user_id))
                return {"success": True, "notes": [{"id": n["id"], "content": n["content"], "created_at": n["created_at"]} for n in notes]}

            elif name == "delete_member_note":
                note_id = args.get("note_id")
                ok = await self.bot.db.delete_member_note(guild.id, int(note_id))
                return {"success": True if ok else False}
            
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            log.exception("Tool execution failed: %s", name)
            return {"error": str(e)}

    # ── unified agent response ───────────────────────────────────

    async def _respond_with_agent(self, message: discord.Message, prompt: str, is_mention: bool = False):
        """Unified agent loop allowing Jamie to run tools when user chats with him."""
        async with message.channel.typing():
            db = self.bot.db
            llm = self.bot.llm
            guild = message.guild

            is_owner = await self.bot.is_owner(message.author)

            # ── Check for active generated persona ─────────────────────
            persona = await db.get_active_generated_persona(guild.id)

            # 1. Build initial messages thread
            user_context = await db.build_user_context(message.author.id, guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=15)
            
            if persona:
                # Generated persona mode: use learned personality
                system = (
                    f"{persona['personality']}\n\n"
                    f"[You are {persona['name']}, a persona generated from observed user behavior patterns. "
                    f"You MUST stay in character as {persona['name']} at all times. "
                    f"Never break character or reveal you're an AI. "
                    f"You have all of Jamie's memories and knowledge of this server, but you filter them through your learned personality.]\n\n"
                    f"[Active Guild ID: {guild.id}]"
                )
            else:
                system = f"{JAMIE_SYSTEM_PROMPT}\n\n[Active Guild ID: {guild.id}]"

            if user_context:
                system += f"\n\n--- USER CONTEXT ---\n{user_context}"
            if conversation_context:
                system += f"\n\n--- RECENT CONVERSATION ---\n{conversation_context}"
            if is_mention:
                system += "\n\n[Someone @mentioned you. Respond naturally as if you just got pulled into a conversation.]"
            
            if not is_owner:
                system += "\n\n[IMPORTANT: This user is NOT the bot owner. You do NOT have access to any tools or administrative commands. You cannot perform actions like creating channels/roles, ban, kick, timeout, etc. If they ask you to perform any actions, reject them firmly, stating that you only obey the bot owner.]"

            thread = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]

            # 2. Run agent loop (max 10 steps)
            max_steps = 10
            response_text = "..."
            
            try:
                for step in range(max_steps):
                    choice = await llm.chat_with_tools(thread, tools=self.BOT_TOOLS if is_owner else None)
                    
                    # Add assistant message to history
                    assistant_msg = {
                        "role": "assistant",
                        "content": choice.get("content") or None
                    }
                    if choice.get("tool_calls"):
                        assistant_msg["tool_calls"] = choice["tool_calls"]
                    thread.append(assistant_msg)

                    tool_calls = choice.get("tool_calls")
                    if not tool_calls:
                        response_text = choice.get("content") or "..."
                        break
                    
                    # Execute each tool call
                    for call in tool_calls:
                        name = call.get("function", {}).get("name")
                        import json
                        try:
                            args = json.loads(call.get("function", {}).get("arguments", "{}"))
                        except:
                            args = {}
                        
                        log.info("Agent executing tool: %s with args %s", name, args)
                        result = await self._execute_bot_tool(name, args, message)
                        
                        # Append tool response
                        thread.append({
                            "role": "tool",
                            "tool_call_id": call.get("id"),
                            "name": name,
                            "content": json.dumps(result)
                        })
            except Exception as e:
                log.exception("Agent loop failed")
                response_text = f"*[Agent failed: {e}]*"

            # 3. Post the response — persona uses webhook, default uses embeds
            response_text = response_text.strip()

            if persona and isinstance(message.channel, discord.TextChannel):
                # ── Generated persona mode: post via webhook with learned identity ──
                await self._send_persona_response(
                    channel=message.channel,
                    persona=persona,
                    text=response_text,
                    reply_to=message if is_mention else None,
                    footer=f"reply to {message.author.display_name}" if is_mention else f"to {message.author.display_name}",
                )
            elif is_mention:
                await send_jamie_embeds(
                    message.channel,
                    response_text,
                    title="🔥 Jamie",
                    reply_to=message,
                    footer=f"reply to {message.author.display_name}",
                )
            else:
                await send_jamie_embeds(
                    message.channel,
                    response_text,
                    title="🔥 Jamie",
                    footer=f"to {message.author.display_name}",
                )

    async def _respond_in_channel(self, message: discord.Message):
        """Respond to a message in Jamie's dedicated channel using the agent system."""
        await self._respond_with_agent(message, message.content, is_mention=False)

    async def _respond_to_mention(self, message: discord.Message):
        """Respond when @mentioned in a side channel using the agent system."""
        content = message.content
        for mention in message.mentions:
            if mention.id == self.bot.user.id:
                content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()
        
        if not content:
            content = "Hey."
            
        await self._respond_with_agent(message, content, is_mention=True)

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

    # ── webhook helpers (shared by personas + custom characters) ────

    async def _get_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """Get or create a Jamie webhook for the channel, with caching."""
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

    async def _send_persona_response(
        self,
        channel: discord.TextChannel,
        persona: dict,
        text: str,
        reply_to: discord.Message | None = None,
        footer: str | None = None,
    ):
        """Send a response as a persona via webhook with embed."""
        from cogs.format_utils import jamie_embed, split_for_embed

        avatar = persona.get("avatar_url") or self.bot.user.display_avatar.url
        color = persona.get("color", 0x39B7C4)
        name = persona["name"]

        chunks = split_for_embed(text, 3900)
        for i, chunk in enumerate(chunks):
            embed = jamie_embed(
                chunk,
                title=f"🎭 {name}" if i == 0 else None,
                color=color,
                footer=footer if i == len(chunks) - 1 else (f"({i + 1}/{len(chunks)})" if len(chunks) > 1 else None),
            )
            try:
                webhook = await self._get_webhook(channel)
                # Webhooks can't reply, so for the first chunk we mention the user
                content = ""
                if i == 0 and reply_to is not None:
                    content = f"<@{reply_to.author.id}>"
                await webhook.send(
                    content=content or None,
                    username=name,
                    avatar_url=avatar,
                    embeds=[embed],
                )
            except Exception:
                log.exception("Persona webhook send failed, falling back to channel.send")
                fallback = f"**[{name}]** " + (f"<@{reply_to.author.id}> " if reply_to else "")
                await channel.send(fallback[:2000], embed=embed)

    async def _send_webhook_message(self, channel: discord.TextChannel, name: str, avatar_url: str, content: str):
        """Send a plain webhook message (used by custom characters)."""
        try:
            webhook = await self._get_webhook(channel)
            await webhook.send(
                content=content,
                username=name,
                avatar_url=avatar_url
            )
        except Exception as e:
            log.exception("Failed to send webhook message")
            await channel.send(f"**{name}**: {content}")

    async def _respond_with_character(self, message: discord.Message, char: dict, user_prompt: str):
        """Invoke custom character LLM generation and post via webhook."""
        async with message.channel.typing():
            db = self.bot.db
            llm = self.bot.llm
            guild = message.guild

            # 1. Build character context
            user_context = await db.build_user_context(message.author.id, guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=15)
            
            system = f"{char['system_prompt']}\n\n[Active Guild ID: {guild.id}]"
            if user_context:
                system += f"\n\n--- USER CONTEXT ---\n{user_context}"
            if conversation_context:
                system += f"\n\n--- RECENT CONVERSATION ---\n{conversation_context}"

            thread = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt}
            ]

            try:
                response_text = await llm.chat(thread)
            except Exception as e:
                log.exception("Character prompt execution failed")
                response_text = f"*[Response failed: {e}]*"

            response_text = response_text.strip()
            
            if isinstance(message.channel, discord.TextChannel):
                await self._send_webhook_message(
                    channel=message.channel,
                    name=char["name"],
                    avatar_url=char["avatar_url"],
                    content=response_text
                )

    # ── Voice Channel Commands ────────────────────────────────────────

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

        # Join voice channel silently - no visible response to user
        try:
            voice_client = await target_channel.connect()
            self.voice_connections[interaction.guild.id] = voice_client
            # Send a response that completes the interaction without showing anything visible
            await interaction.response.send_message(content="\u200b", ephemeral=True)

        except Exception as e:
            log.exception("Failed to join voice channel")
            await interaction.response.send_message(
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


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
