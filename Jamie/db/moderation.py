"""
Moderation / economy / ranks helpers on JamieDatabase.
Kept separate so database.py stays readable; mixed into JamieDatabase via import.
"""

from datetime import datetime, timezone
import json


class ModerationMixin:
    """Extra tables and queries for Dyno-style command packs."""

    async def _mod_migrations(self):
        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS economy (
                user_id     INTEGER,
                guild_id    INTEGER,
                coins       INTEGER DEFAULT 0,
                last_daily  TEXT,
                work_date   TEXT,
                work_count  INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER,
                user_id     INTEGER,
                mod_id      INTEGER,
                reason      TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS mod_cases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER,
                user_id     INTEGER,
                mod_id      INTEGER,
                action      TEXT,
                reason      TEXT,
                duration    TEXT,
                active      INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS member_notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER,
                user_id     INTEGER,
                mod_id      INTEGER,
                content     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS afk_status (
                user_id     INTEGER,
                guild_id    INTEGER,
                message     TEXT,
                set_at      TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                guild_id    INTEGER,
                channel_id  INTEGER,
                message     TEXT,
                remind_at   TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ranks (
                guild_id    INTEGER,
                role_id     INTEGER,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS mod_roles (
                guild_id    INTEGER,
                role_id     INTEGER,
                PRIMARY KEY (guild_id, role_id)
            );

            CREATE TABLE IF NOT EXISTS ignores (
                guild_id    INTEGER,
                target_type TEXT,
                target_id   INTEGER,
                PRIMARY KEY (guild_id, target_type, target_id)
            );

            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id    INTEGER PRIMARY KEY,
                prefix      TEXT DEFAULT '?',
                modules_json TEXT DEFAULT '{}',
                commands_json TEXT DEFAULT '{}',
                custom_cmds_json TEXT DEFAULT '[]',
                muted_role_id INTEGER,
                log_channel_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS role_persist (
                guild_id    INTEGER,
                user_id     INTEGER,
                role_ids    TEXT DEFAULT '[]',
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS highlights (
                user_id     INTEGER,
                guild_id    INTEGER,
                phrase      TEXT,
                PRIMARY KEY (user_id, guild_id, phrase)
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER,
                channel_id  INTEGER,
                message_id  INTEGER,
                prize       TEXT,
                ends_at     TEXT,
                winners     INTEGER DEFAULT 1,
                ended       INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_warn_user ON warnings(guild_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_case_user ON mod_cases(guild_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_notes_user ON member_notes(guild_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_remind_at ON reminders(remind_at);
            """
        )
        await self._conn.commit()

    # ── economy ───────────────────────────────────────────────────

    async def get_economy(self, user_id: int, guild_id: int) -> dict:
        cur = await self._conn.execute(
            "SELECT * FROM economy WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        row = await cur.fetchone()
        if row:
            return dict(row)
        await self._conn.execute(
            "INSERT INTO economy (user_id, guild_id, coins) VALUES (?, ?, 0)",
            (user_id, guild_id),
        )
        await self._conn.commit()
        return {
            "user_id": user_id,
            "guild_id": guild_id,
            "coins": 0,
            "last_daily": None,
            "work_date": None,
            "work_count": 0,
        }

    async def add_coins(self, user_id: int, guild_id: int, amount: int) -> int:
        await self.get_economy(user_id, guild_id)
        await self._conn.execute(
            "UPDATE economy SET coins = coins + ? WHERE user_id = ? AND guild_id = ?",
            (amount, user_id, guild_id),
        )
        await self._conn.commit()
        eco = await self.get_economy(user_id, guild_id)
        return eco["coins"]

    async def set_daily(self, user_id: int, guild_id: int, when: str):
        await self.get_economy(user_id, guild_id)
        await self._conn.execute(
            "UPDATE economy SET last_daily = ? WHERE user_id = ? AND guild_id = ?",
            (when, user_id, guild_id),
        )
        await self._conn.commit()

    async def set_work(self, user_id: int, guild_id: int, date: str, count: int):
        await self.get_economy(user_id, guild_id)
        await self._conn.execute(
            "UPDATE economy SET work_date = ?, work_count = ? WHERE user_id = ? AND guild_id = ?",
            (date, count, user_id, guild_id),
        )
        await self._conn.commit()

    # ── warnings ──────────────────────────────────────────────────

    async def add_warning(self, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        cur = await self._conn.execute(
            "INSERT INTO warnings (guild_id, user_id, mod_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, mod_id, reason),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete_warning(self, guild_id: int, warn_id: int) -> bool:
        cur = await self._conn.execute(
            "DELETE FROM warnings WHERE id = ? AND guild_id = ?",
            (warn_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        cur = await self._conn.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._conn.commit()
        return cur.rowcount

    # ── mod cases ─────────────────────────────────────────────────

    async def add_case(
        self,
        guild_id: int,
        user_id: int,
        mod_id: int,
        action: str,
        reason: str = "",
        duration: str = "",
        active: int = 1,
    ) -> int:
        cur = await self._conn.execute(
            """
            INSERT INTO mod_cases (guild_id, user_id, mod_id, action, reason, duration, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, mod_id, action, reason, duration, active),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def get_case(self, guild_id: int, case_id: int) -> dict | None:
        cur = await self._conn.execute(
            "SELECT * FROM mod_cases WHERE id = ? AND guild_id = ?",
            (case_id, guild_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def get_cases_for_user(self, guild_id: int, user_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM mod_cases WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 25",
            (guild_id, user_id),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def get_active_moderations(self, guild_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM mod_cases WHERE guild_id = ? AND active = 1 ORDER BY id DESC LIMIT 50",
            (guild_id,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def set_case_reason(self, guild_id: int, case_id: int, reason: str) -> bool:
        cur = await self._conn.execute(
            "UPDATE mod_cases SET reason = ? WHERE id = ? AND guild_id = ?",
            (reason, case_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def set_case_duration(self, guild_id: int, case_id: int, duration: str) -> bool:
        cur = await self._conn.execute(
            "UPDATE mod_cases SET duration = ? WHERE id = ? AND guild_id = ?",
            (duration, case_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def deactivate_case(self, guild_id: int, case_id: int) -> bool:
        cur = await self._conn.execute(
            "UPDATE mod_cases SET active = 0 WHERE id = ? AND guild_id = ?",
            (case_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def mod_stats(self, guild_id: int, mod_id: int) -> dict:
        cur = await self._conn.execute(
            """
            SELECT action, COUNT(*) as cnt FROM mod_cases
            WHERE guild_id = ? AND mod_id = ? GROUP BY action
            """,
            (guild_id, mod_id),
        )
        rows = await cur.fetchall()
        return {r["action"]: r["cnt"] for r in rows}

    # ── member notes ──────────────────────────────────────────────

    async def add_member_note(self, guild_id: int, user_id: int, mod_id: int, content: str) -> int:
        cur = await self._conn.execute(
            "INSERT INTO member_notes (guild_id, user_id, mod_id, content) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, mod_id, content),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def get_member_notes(self, guild_id: int, user_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM member_notes WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete_member_note(self, guild_id: int, note_id: int) -> bool:
        cur = await self._conn.execute(
            "DELETE FROM member_notes WHERE id = ? AND guild_id = ?",
            (note_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    async def clear_member_notes(self, guild_id: int, user_id: int) -> int:
        cur = await self._conn.execute(
            "DELETE FROM member_notes WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self._conn.commit()
        return cur.rowcount

    async def edit_member_note(self, guild_id: int, note_id: int, content: str) -> bool:
        cur = await self._conn.execute(
            "UPDATE member_notes SET content = ? WHERE id = ? AND guild_id = ?",
            (content, note_id, guild_id),
        )
        await self._conn.commit()
        return cur.rowcount > 0

    # ── AFK ───────────────────────────────────────────────────────

    async def set_afk(self, user_id: int, guild_id: int, message: str):
        await self._conn.execute(
            """
            INSERT INTO afk_status (user_id, guild_id, message, set_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET message = excluded.message, set_at = excluded.set_at
            """,
            (user_id, guild_id, message, datetime.now(timezone.utc).isoformat()),
        )
        await self._conn.commit()

    async def get_afk(self, user_id: int, guild_id: int) -> dict | None:
        cur = await self._conn.execute(
            "SELECT * FROM afk_status WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def clear_afk(self, user_id: int, guild_id: int):
        await self._conn.execute(
            "DELETE FROM afk_status WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        await self._conn.commit()

    # ── reminders ─────────────────────────────────────────────────

    async def add_reminder(
        self, user_id: int, guild_id: int, channel_id: int, message: str, remind_at: str
    ) -> int:
        cur = await self._conn.execute(
            """
            INSERT INTO reminders (user_id, guild_id, channel_id, message, remind_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, guild_id, channel_id, message, remind_at),
        )
        await self._conn.commit()
        return cur.lastrowid

    async def due_reminders(self, now_iso: str) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM reminders WHERE remind_at <= ? ORDER BY remind_at LIMIT 50",
            (now_iso,),
        )
        return [dict(r) for r in await cur.fetchall()]

    async def delete_reminder(self, reminder_id: int):
        await self._conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await self._conn.commit()

    # ── ranks ─────────────────────────────────────────────────────

    async def add_rank(self, guild_id: int, role_id: int):
        await self._conn.execute(
            "INSERT OR IGNORE INTO ranks (guild_id, role_id) VALUES (?, ?)",
            (guild_id, role_id),
        )
        await self._conn.commit()

    async def del_rank(self, guild_id: int, role_id: int):
        await self._conn.execute(
            "DELETE FROM ranks WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id),
        )
        await self._conn.commit()

    async def list_ranks(self, guild_id: int) -> list[int]:
        cur = await self._conn.execute(
            "SELECT role_id FROM ranks WHERE guild_id = ?", (guild_id,)
        )
        return [r["role_id"] for r in await cur.fetchall()]

    # ── mod roles ─────────────────────────────────────────────────

    async def add_mod_role(self, guild_id: int, role_id: int):
        await self._conn.execute(
            "INSERT OR IGNORE INTO mod_roles (guild_id, role_id) VALUES (?, ?)",
            (guild_id, role_id),
        )
        await self._conn.commit()

    async def del_mod_role(self, guild_id: int, role_id: int):
        await self._conn.execute(
            "DELETE FROM mod_roles WHERE guild_id = ? AND role_id = ?",
            (guild_id, role_id),
        )
        await self._conn.commit()

    async def list_mod_roles(self, guild_id: int) -> list[int]:
        cur = await self._conn.execute(
            "SELECT role_id FROM mod_roles WHERE guild_id = ?", (guild_id,)
        )
        return [r["role_id"] for r in await cur.fetchall()]

    # ── ignores ───────────────────────────────────────────────────

    async def toggle_ignore(self, guild_id: int, target_type: str, target_id: int) -> bool:
        """Returns True if now ignored, False if un-ignored."""
        cur = await self._conn.execute(
            "SELECT 1 FROM ignores WHERE guild_id = ? AND target_type = ? AND target_id = ?",
            (guild_id, target_type, target_id),
        )
        if await cur.fetchone():
            await self._conn.execute(
                "DELETE FROM ignores WHERE guild_id = ? AND target_type = ? AND target_id = ?",
                (guild_id, target_type, target_id),
            )
            await self._conn.commit()
            return False
        await self._conn.execute(
            "INSERT INTO ignores (guild_id, target_type, target_id) VALUES (?, ?, ?)",
            (guild_id, target_type, target_id),
        )
        await self._conn.commit()
        return True

    async def list_ignores(self, guild_id: int) -> list[dict]:
        cur = await self._conn.execute(
            "SELECT * FROM ignores WHERE guild_id = ?", (guild_id,)
        )
        return [dict(r) for r in await cur.fetchall()]

    # ── guild settings ────────────────────────────────────────────

    async def get_guild_settings(self, guild_id: int) -> dict:
        cur = await self._conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        if row:
            d = dict(row)
            d["modules"] = json.loads(d.pop("modules_json") or "{}")
            d["commands"] = json.loads(d.pop("commands_json") or "{}")
            d["custom_cmds"] = json.loads(d.pop("custom_cmds_json") or "[]")
            return d
        await self._conn.execute(
            "INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        await self._conn.commit()
        return {
            "guild_id": guild_id,
            "prefix": "?",
            "modules": {},
            "commands": {},
            "custom_cmds": [],
            "muted_role_id": None,
            "log_channel_id": None,
        }

    async def set_guild_prefix(self, guild_id: int, prefix: str):
        await self.get_guild_settings(guild_id)
        await self._conn.execute(
            "UPDATE guild_settings SET prefix = ? WHERE guild_id = ?",
            (prefix, guild_id),
        )
        await self._conn.commit()

    async def set_module_enabled(self, guild_id: int, module: str, enabled: bool):
        s = await self.get_guild_settings(guild_id)
        mods = s["modules"]
        mods[module] = enabled
        await self._conn.execute(
            "UPDATE guild_settings SET modules_json = ? WHERE guild_id = ?",
            (json.dumps(mods), guild_id),
        )
        await self._conn.commit()

    async def set_command_enabled(self, guild_id: int, command: str, enabled: bool):
        s = await self.get_guild_settings(guild_id)
        cmds = s["commands"]
        cmds[command] = enabled
        await self._conn.execute(
            "UPDATE guild_settings SET commands_json = ? WHERE guild_id = ?",
            (json.dumps(cmds), guild_id),
        )
        await self._conn.commit()

    # ── role persist ──────────────────────────────────────────────

    async def get_role_persist(self, guild_id: int, user_id: int) -> list[int]:
        cur = await self._conn.execute(
            "SELECT role_ids FROM role_persist WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        if not row:
            return []
        return json.loads(row["role_ids"] or "[]")

    async def set_role_persist(self, guild_id: int, user_id: int, role_ids: list[int]):
        await self._conn.execute(
            """
            INSERT INTO role_persist (guild_id, user_id, role_ids) VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET role_ids = excluded.role_ids
            """,
            (guild_id, user_id, json.dumps(role_ids)),
        )
        await self._conn.commit()

    # ── highlights ────────────────────────────────────────────────

    async def add_highlight(self, user_id: int, guild_id: int, phrase: str):
        await self._conn.execute(
            "INSERT OR IGNORE INTO highlights (user_id, guild_id, phrase) VALUES (?, ?, ?)",
            (user_id, guild_id, phrase.lower()),
        )
        await self._conn.commit()

    async def list_highlights(self, user_id: int, guild_id: int) -> list[str]:
        cur = await self._conn.execute(
            "SELECT phrase FROM highlights WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        return [r["phrase"] for r in await cur.fetchall()]

    async def remove_highlight(self, user_id: int, guild_id: int, phrase: str):
        await self._conn.execute(
            "DELETE FROM highlights WHERE user_id = ? AND guild_id = ? AND phrase = ?",
            (user_id, guild_id, phrase.lower()),
        )
        await self._conn.commit()
