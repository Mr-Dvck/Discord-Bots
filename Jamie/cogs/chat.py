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

    # ── Agent Tools List ──────────────────────────────────────────

    BOT_TOOLS = [
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
        }
    ]

    async def _execute_bot_tool(self, name: str, args: dict, guild: discord.Guild) -> dict:
        try:
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

            # 1. Build initial messages thread
            user_context = await db.build_user_context(message.author.id, guild.id)
            conversation_context = await db.build_conversation_context(message.channel.id, limit=15)
            
            system = f"{llm.JAMIE_SYSTEM_PROMPT}\n\n[Active Guild ID: {guild.id}]"
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
                        result = await self._execute_bot_tool(name, args, guild)
                        
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

            # 3. Post the response
            response_text = response_text.strip()
            if is_mention:
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


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
