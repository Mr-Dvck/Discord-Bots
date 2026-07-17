"""
Jamie Database Layer — SQLite async wrapper
Tables: server_config, user_profiles, message_memory, server_map + mod/economy packs
"""

import aiosqlite
import json
import os
from datetime import datetime, timezone

from db.moderation import ModerationMixin

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jamie.db")


class JamieDatabase(ModerationMixin):
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._conn: aiosqlite.Connection | None = None

    # ── lifecycle ────────────────────────────────────────────────

    async def connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._run_migrations()
        await self._mod_migrations()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _run_migrations(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id    INTEGER PRIMARY KEY,
                channel_id  INTEGER,
                prefix      TEXT DEFAULT '/',
                auto_respond INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id     INTEGER,
                guild_id    INTEGER,
                username    TEXT,
                display_name TEXT,
                avatar_url  TEXT,
                joined_at   TEXT,
                message_count INTEGER DEFAULT 0,
                personality_summary TEXT DEFAULT '',
                interests   TEXT DEFAULT '',
                notes       TEXT DEFAULT '',
                last_seen   TEXT,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS message_memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id  INTEGER,
                guild_id    INTEGER,
                channel_id  INTEGER,
                channel_name TEXT,
                user_id     INTEGER,
                username    TEXT,
                content     TEXT,
                timestamp   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS server_map (
                guild_id      INTEGER,
                channel_id    INTEGER PRIMARY KEY,
                channel_name  TEXT,
                channel_type  TEXT,
                category_name TEXT DEFAULT '',
                topic         TEXT DEFAULT '',
                position      INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_msg_guild   ON message_memory(guild_id);
            CREATE INDEX IF NOT EXISTS idx_msg_user     ON message_memory(user_id, guild_id);
            CREATE INDEX IF NOT EXISTS idx_msg_channel   ON message_memory(channel_id);
            CREATE INDEX IF NOT EXISTS idx_msg_time     ON message_memory(timestamp);
            CREATE INDEX IF NOT EXISTS idx_profile_guild ON user_profiles(guild_id);

            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id       INTEGER PRIMARY KEY,
                enabled        INTEGER DEFAULT 0,
                channel_id     INTEGER,
                message        TEXT DEFAULT 'Welcome {user} — you are now Certified.',
                image_line     TEXT DEFAULT 'is now Certified',
                show_avatar    INTEGER DEFAULT 1,
                dm_on_join     INTEGER DEFAULT 0,
                background_path TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS starboard_config (
                guild_id       INTEGER PRIMARY KEY,
                enabled        INTEGER DEFAULT 0,
                channel_id     INTEGER,
                min_stars      INTEGER DEFAULT 3
            );

            CREATE TABLE IF NOT EXISTS starboard_messages (
                orig_message_id      INTEGER PRIMARY KEY,
                starboard_message_id INTEGER NOT NULL
            );
        """)
        await self._conn.commit()

    # ── server config ────────────────────────────────────────────

    async def set_channel(self, guild_id: int, channel_id: int):
        await self._conn.execute(
            "INSERT INTO server_config (guild_id, channel_id) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET channel_id = ?",
            (guild_id, channel_id, channel_id),
        )
        await self._conn.commit()

    async def get_channel(self, guild_id: int) -> int | None:
        cur = await self._conn.execute(
            "SELECT channel_id FROM server_config WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        return row["channel_id"] if row else None

    async def get_config(self, guild_id: int) -> dict | None:
        cur = await self._conn.execute(
            "SELECT * FROM server_config WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def is_setup(self, guild_id: int) -> bool:
        return await self.get_channel(guild_id) is not None

    # ── user profiles ─────────────────────────────────────────────

    async def upsert_user(self, user_id: int, guild_id: int, **kwargs):
        defaults = {
            "username": "", "display_name": "", "avatar_url": "",
            "joined_at": datetime.now(timezone.utc).isoformat(),
            "message_count": 0, "personality_summary": "",
            "interests": "", "notes": "", "last_seen": "",
        }
        defaults.update(kwargs)

        await self._conn.execute(
            """
            INSERT INTO user_profiles
                (user_id, guild_id, username, display_name, avatar_url,
                 joined_at, message_count, personality_summary, interests, notes, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
                username     = excluded.username,
                display_name = excluded.display_name,
                avatar_url   = excluded.avatar_url,
                last_seen    = excluded.last_seen,
                message_count = excluded.message_count,
                personality_summary = excluded.personality_summary,
                interests    = excluded.interests,
                notes        = excluded.notes
            """,
            (
                user_id, guild_id, defaults["username"], defaults["display_name"],
                defaults["avatar_url"], defaults["joined_at"],
                defaults["message_count"], defaults["personality_summary"],
                defaults["interests"], defaults["notes"], defaults["last_seen"],
            ),
        )
        await self._conn.commit()

    async def get_user_profile(self, user_id: int, guild_id: int) -> dict | None:
        cur = await self._conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def increment_message_count(self, user_id: int, guild_id: int):
        cur = await self._conn.execute(
            "SELECT message_count FROM user_profiles WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        row = await cur.fetchone()
        count = (row["message_count"] if row else 0) + 1
        await self.upsert_user(user_id, guild_id, message_count=count)

    async def update_user_notes(self, user_id: int, guild_id: int, notes: str):
        await self._conn.execute(
            "UPDATE user_profiles SET notes = ? WHERE user_id = ? AND guild_id = ?",
            (notes, user_id, guild_id),
        )
        await self._conn.commit()

    async def update_user_personality(self, user_id: int, guild_id: int, summary: str, interests: str):
        await self._conn.execute(
            "UPDATE user_profiles SET personality_summary = ?, interests = ? WHERE user_id = ? AND guild_id = ?",
            (summary, interests, user_id, guild_id),
        )
        await self._conn.commit()

    async def get_all_profiles(self, guild_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM user_profiles WHERE guild_id = ? ORDER BY message_count DESC",
            (guild_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    # ── message memory ────────────────────────────────────────────

    async def store_message(self, message_id: int, guild_id: int, channel_id: int,
                            channel_name: str, user_id: int, username: str, content: str):
        await self._conn.execute(
            """
            INSERT INTO message_memory
                (message_id, guild_id, channel_id, channel_name, user_id, username, content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, guild_id, channel_id, channel_name, user_id, username, content),
        )
        await self._conn.commit()

    async def get_recent_messages(self, guild_id: int, limit: int = 50) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM message_memory WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?",
            (guild_id, limit),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_user_messages(self, user_id: int, guild_id: int, limit: int = 30) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM message_memory WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, guild_id, limit),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_channel_messages(self, channel_id: int, limit: int = 50) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM message_memory WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?",
            (channel_id, limit),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def search_messages(self, guild_id: int, query: str, limit: int = 20) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM message_memory WHERE guild_id = ? AND content LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (guild_id, f"%{query}%", limit),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def prune_old_messages(self, guild_id: int, keep: int = 5000):
        """Keep only the most recent `keep` messages for a guild."""
        cur = await self._conn.execute(
            "SELECT COUNT(*) as cnt FROM message_memory WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cur.fetchone()
        if row["cnt"] > keep:
            await self._conn.execute(
                """
                DELETE FROM message_memory WHERE guild_id = ? AND id NOT IN (
                    SELECT id FROM message_memory WHERE guild_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                )
                """,
                (guild_id, guild_id, keep),
            )
            await self._conn.commit()

    # ── server map ────────────────────────────────────────────────

    async def upsert_channel(self, guild_id: int, channel_id: int, channel_name: str,
                             channel_type: str, category_name: str = "", topic: str = "",
                             position: int = 0):
        await self._conn.execute(
            """
            INSERT INTO server_map
                (guild_id, channel_id, channel_name, channel_type, category_name, topic, position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_name  = excluded.channel_name,
                channel_type  = excluded.channel_type,
                category_name = excluded.category_name,
                topic         = excluded.topic,
                position      = excluded.position
            """,
            (guild_id, channel_id, channel_name, channel_type, category_name, topic, position),
        )
        await self._conn.commit()

    async def get_server_map(self, guild_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM server_map WHERE guild_id = ? ORDER BY position",
            (guild_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete_channel(self, channel_id: int):
        await self._conn.execute(
            "DELETE FROM server_map WHERE channel_id = ?", (channel_id,)
        )
        await self._conn.commit()

    # ── context builder for LLM ────────────────────────────────────

    async def build_user_context(self, user_id: int, guild_id: int) -> str:
        """Build a context string about a user for the LLM."""
        profile = await self.get_user_profile(user_id, guild_id)
        if not profile:
            return "No profile data available for this user."

        recent = await self.get_user_messages(user_id, guild_id, limit=10)
        msg_snippets = "\n".join(
            f"  [{m['timestamp'][:16]}] #{m['channel_name']}: {m['content'][:120]}"
            for m in recent
        )

        return (
            f"User: {profile['display_name']} (@{profile['username']})\n"
            f"Messages sent: {profile['message_count']}\n"
            f"Personality: {profile['personality_summary'] or 'Unknown'}\n"
            f"Interests: {profile['interests'] or 'Unknown'}\n"
            f"Notes: {profile['notes'] or 'None'}\n"
            f"Last seen: {profile['last_seen'] or 'Unknown'}\n"
            f"Recent messages:\n{msg_snippets}"
        )

    async def build_conversation_context(self, channel_id: int, limit: int = 20) -> str:
        """Build recent conversation context for the LLM."""
        messages = await self.get_channel_messages(channel_id, limit)
        lines = []
        for m in reversed(messages):
            lines.append(f"[{m['username']}]: {m['content'][:200]}")
        return "\n".join(lines)

    # ── welcome (Dyno-style join banners) ─────────────────────────

    _WELCOME_DEFAULTS = {
        "enabled": 0,
        "channel_id": None,
        "message": "Welcome {user} — you are now Certified.",
        "image_line": "is now Certified",
        "show_avatar": 0,
        "dm_on_join": 0,
        "background_path": "",
    }

    async def get_welcome_config(self, guild_id: int) -> dict:
        cur = await self._conn.execute(
            "SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {"guild_id": guild_id, **self._WELCOME_DEFAULTS}

    async def upsert_welcome_config(self, guild_id: int, **kwargs):
        current = await self.get_welcome_config(guild_id)
        merged = {**self._WELCOME_DEFAULTS, **current, **kwargs, "guild_id": guild_id}
        await self._conn.execute(
            """
            INSERT INTO welcome_config
                (guild_id, enabled, channel_id, message, image_line,
                 show_avatar, dm_on_join, background_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                enabled         = excluded.enabled,
                channel_id      = excluded.channel_id,
                message         = excluded.message,
                image_line      = excluded.image_line,
                show_avatar     = excluded.show_avatar,
                dm_on_join      = excluded.dm_on_join,
                background_path = excluded.background_path
            """,
            (
                guild_id,
                int(merged.get("enabled") or 0),
                merged.get("channel_id"),
                merged.get("message") or self._WELCOME_DEFAULTS["message"],
                merged.get("image_line") or self._WELCOME_DEFAULTS["image_line"],
                int(merged.get("show_avatar", 1)),
                int(merged.get("dm_on_join") or 0),
                merged.get("background_path") or "",
            ),
        )
        await self._conn.commit()
        return await self.get_welcome_config(guild_id)

    # ── starboard ─────────────────────────────────────────────────

    _STARBOARD_DEFAULTS = {
        "enabled": 0,
        "channel_id": None,
        "min_stars": 3,
    }

    async def get_starboard_config(self, guild_id: int) -> dict:
        cur = await self._conn.execute(
            "SELECT * FROM starboard_config WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {"guild_id": guild_id, **self._STARBOARD_DEFAULTS}

    async def upsert_starboard_config(self, guild_id: int, **kwargs):
        current = await self.get_starboard_config(guild_id)
        merged = {**self._STARBOARD_DEFAULTS, **current, **kwargs, "guild_id": guild_id}
        await self._conn.execute(
            """
            INSERT INTO starboard_config (guild_id, enabled, channel_id, min_stars)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                enabled    = excluded.enabled,
                channel_id = excluded.channel_id,
                min_stars  = excluded.min_stars
            """,
            (
                guild_id,
                int(merged.get("enabled") or 0),
                merged.get("channel_id"),
                int(merged.get("min_stars") or 3),
            ),
        )
        await self._conn.commit()
        return await self.get_starboard_config(guild_id)

    async def get_starboard_message(self, orig_message_id: int) -> int | None:
        cur = await self._conn.execute(
            "SELECT starboard_message_id FROM starboard_messages WHERE orig_message_id = ?",
            (orig_message_id,),
        )
        row = await cur.fetchone()
        return row["starboard_message_id"] if row else None

    async def save_starboard_message(self, orig_message_id: int, starboard_message_id: int):
        await self._conn.execute(
            "INSERT OR REPLACE INTO starboard_messages (orig_message_id, starboard_message_id) VALUES (?, ?)",
            (orig_message_id, starboard_message_id),
        )
        await self._conn.commit()

    async def delete_starboard_message(self, orig_message_id: int):
        await self._conn.execute(
            "DELETE FROM starboard_messages WHERE orig_message_id = ?",
            (orig_message_id,),
        )
        await self._conn.commit()
