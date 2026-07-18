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

            CREATE TABLE IF NOT EXISTS custom_characters (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id      INTEGER,
                name          TEXT,
                avatar_url    TEXT,
                system_prompt TEXT,
                shortcut      TEXT,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS behavior_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER,
                user_id         INTEGER,
                message_content TEXT,
                behavior_tags   TEXT,  -- JSON array of observed behaviors
                sentiment_score REAL DEFAULT 0.0,
                timestamp       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS generated_personas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id        INTEGER,
                name            TEXT NOT NULL,
                avatar_url      TEXT DEFAULT '',
                personality    TEXT DEFAULT '',
                color           INTEGER DEFAULT 0x39B7C4,
                source_patterns TEXT,  -- JSON of behavior patterns that created this persona
                confidence_score REAL DEFAULT 0.0,
                is_active       INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_behavior_guild ON behavior_logs(guild_id);
            CREATE INDEX IF NOT EXISTS idx_behavior_user ON behavior_logs(user_id, guild_id);
            CREATE INDEX IF NOT EXISTS idx_personas_guild ON generated_personas(guild_id);
        """)
        await self._conn.commit()

        # ── additive migrations (safe ALTERs for existing DBs) ────────
        try:
            await self._conn.execute(
                "ALTER TABLE server_config ADD COLUMN active_persona_id INTEGER DEFAULT NULL"
            )
            await self._conn.commit()
        except Exception:
            pass  # column already exists
        
        try:
            await self._conn.execute(
                "ALTER TABLE server_config ADD COLUMN notes_log_channel_id INTEGER DEFAULT NULL"
            )
            await self._conn.commit()
        except Exception:
            pass  # column already exists
        
        try:
            await self._conn.execute(
                "ALTER TABLE server_config ADD COLUMN brain_channel_id INTEGER DEFAULT NULL"
            )
            await self._conn.commit()
        except Exception:
            pass  # column already exists

        try:
            await self._conn.execute(
                "ALTER TABLE server_config ADD COLUMN omnipresent_mode INTEGER DEFAULT 1"
            )
            await self._conn.commit()
        except Exception:
            pass  # column already exists

        try:
            await self._conn.execute(
                "ALTER TABLE server_config ADD COLUMN omnipresent_chance REAL DEFAULT 0.03"
            )
            await self._conn.commit()
        except Exception:
            pass  # column already exists

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

    # ── custom characters ─────────────────────────────────────────

    async def add_custom_character(self, guild_id: int, name: str, avatar_url: str, system_prompt: str, shortcut: str):
        await self._conn.execute(
            "INSERT INTO custom_characters (guild_id, name, avatar_url, system_prompt, shortcut) VALUES (?, ?, ?, ?, ?)",
            (guild_id, name, avatar_url, system_prompt, shortcut),
        )
        await self._conn.commit()

    async def get_custom_characters(self, guild_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM custom_characters WHERE guild_id = ? ORDER BY id DESC",
            (guild_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete_custom_character(self, guild_id: int, char_id: int) -> bool:
        cur = await self._conn.execute(
            "DELETE FROM custom_characters WHERE id = ? AND guild_id = ?",
            (char_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def get_custom_character_by_shortcut(self, guild_id: int, shortcut: str) -> dict | None:
        cur = await self._conn.execute(
            "SELECT * FROM custom_characters WHERE guild_id = ? AND LOWER(shortcut) = ?",
            (guild_id, shortcut.lower()),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    # ── behavior logging (anonymous conversation patterns) ──────────

    async def log_behavior(self, guild_id: int, user_id: int, message_content: str,
                          behavior_tags: list[str], sentiment_score: float = 0.0):
        """Log user behavior for persona generation."""
        import json
        cur = await self._conn.execute(
            "INSERT INTO behavior_logs (guild_id, user_id, message_content, behavior_tags, sentiment_score) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, message_content, json.dumps(behavior_tags), sentiment_score),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def get_behavior_patterns(self, guild_id: int, limit: int = 100) -> list[dict]:
        """Get recent behavior patterns for analysis."""
        cur = await self._conn.execute(
            "SELECT * FROM behavior_logs WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?",
            (guild_id, limit),
        )
        patterns = []
        for row in await cur.fetchall():
            pattern = dict(row)
            import json
            pattern["behavior_tags"] = json.loads(pattern["behavior_tags"] or "[]")
            patterns.append(pattern)
        return patterns

    async def get_user_behavior_summary(self, guild_id: int, user_id: int) -> dict:
        """Get behavior summary for a specific user."""
        cur = await self._conn.execute(
            "SELECT behavior_tags, sentiment_score, COUNT(*) as message_count "
            "FROM behavior_logs WHERE guild_id = ? AND user_id = ? "
            "GROUP BY behavior_tags, sentiment_score",
            (guild_id, user_id),
        )
        import json
        all_tags = []
        sentiments = []
        total_messages = 0
        
        for row in await cur.fetchall():
            tags = json.loads(row["behavior_tags"] or "[]")
            all_tags.extend(tags)
            sentiments.append(row["sentiment_score"])
            total_messages += row["message_count"]
        
        # Count tag frequencies
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        return {
            "user_id": user_id,
            "total_messages": total_messages,
            "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "avg_sentiment": avg_sentiment,
            "tag_diversity": len(tag_counts),
        }

    # ── generated personas (from behavior analysis) ─────────────────

    async def create_generated_persona(self, guild_id: int, name: str, personality: str,
                                      source_patterns: dict, confidence_score: float = 0.0,
                                      avatar_url: str = "", color: int = 0x39B7C4) -> int:
        """Create a persona generated from behavior analysis."""
        import json
        cur = await self._conn.execute(
            "INSERT INTO generated_personas (guild_id, name, avatar_url, personality, "
            "source_patterns, confidence_score, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (guild_id, name, avatar_url, personality, json.dumps(source_patterns), confidence_score),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def get_generated_personas(self, guild_id: int) -> list[dict]:
        """Get all generated personas for a guild."""
        cur = await self._conn.execute(
            "SELECT * FROM generated_personas WHERE guild_id = ? ORDER BY created_at DESC",
            (guild_id,),
        )
        personas = []
        for row in await cur.fetchall():
            persona = dict(row)
            import json
            persona["source_patterns"] = json.loads(persona["source_patterns"] or "{}")
            personas.append(persona)
        return personas

    async def get_active_generated_persona(self, guild_id: int) -> dict | None:
        """Get the currently active generated persona."""
        cur = await self._conn.execute(
            "SELECT * FROM generated_personas WHERE guild_id = ? AND is_active = 1 LIMIT 1",
            (guild_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        persona = dict(row)
        import json
        persona["source_patterns"] = json.loads(persona["source_patterns"] or "{}")
        return persona

    async def set_active_generated_persona(self, guild_id: int, persona_id: int) -> None:
        """Set a generated persona as active (deactivates others)."""
        await self._conn.execute(
            "UPDATE generated_personas SET is_active = 0 WHERE guild_id = ?",
            (guild_id,),
        )
        await self._conn.execute(
            "UPDATE generated_personas SET is_active = 1 WHERE id = ? AND guild_id = ?",
            (persona_id, guild_id),
        )
        await self._conn.commit()

    async def clear_active_persona(self, guild_id: int) -> None:
        """Clear all active personas (return to default Jamie)."""
        await self._conn.execute(
            "UPDATE generated_personas SET is_active = 0 WHERE guild_id = ?",
            (guild_id,),
        )
        await self._conn.commit()

    # ── channel configuration for behavior system ─────────────────────

    async def set_notes_log_channel(self, guild_id: int, channel_id: int) -> None:
        """Set the channel for anonymous behavior logging."""
        await self._conn.execute(
            "UPDATE server_config SET notes_log_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )
        await self._conn.commit()

    async def get_notes_log_channel(self, guild_id: int) -> int | None:
        """Get the notes log channel ID."""
        cur = await self._conn.execute(
            "SELECT notes_log_channel_id FROM server_config WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cur.fetchone()
        return row["notes_log_channel_id"] if row else None

    async def set_brain_channel(self, guild_id: int, channel_id: int) -> None:
        """Set the channel for posting generated personas."""
        await self._conn.execute(
            "UPDATE server_config SET brain_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )
        await self._conn.commit()

    async def get_brain_channel(self, guild_id: int) -> int | None:
        """Get the brain channel ID."""
        cur = await self._conn.execute(
            "SELECT brain_channel_id FROM server_config WHERE guild_id = ?",
            (guild_id,),
        )
        row = await cur.fetchone()
        return row["brain_channel_id"] if row else None

    # ── Omnipresent Mode ────────────────────────────────────────────

    async def set_omnipresent_mode(self, guild_id: int, enabled: bool) -> None:
        await self._conn.execute(
            "INSERT INTO server_config (guild_id, omnipresent_mode) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET omnipresent_mode = ?",
            (guild_id, 1 if enabled else 0, 1 if enabled else 0)
        )
        await self._conn.commit()

    async def get_omnipresent_mode(self, guild_id: int) -> bool:
        cur = await self._conn.execute(
            "SELECT omnipresent_mode FROM server_config WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cur.fetchone()
        return bool(row["omnipresent_mode"]) if row else True  # Default to enabled

    async def set_omnipresent_chance(self, guild_id: int, chance: float) -> None:
        await self._conn.execute(
            "INSERT INTO server_config (guild_id, omnipresent_chance) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET omnipresent_chance = ?",
            (guild_id, chance, chance)
        )
        await self._conn.commit()

    async def get_omnipresent_chance(self, guild_id: int) -> float:
        cur = await self._conn.execute(
            "SELECT omnipresent_chance FROM server_config WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cur.fetchone()
        return row["omnipresent_chance"] if row else 0.03  # Default to 3%
