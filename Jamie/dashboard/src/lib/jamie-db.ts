/**
 * Read-only access to Jamie bot SQLite memory (user_profiles, message_memory).
 * Local path: ../data/jamie.db relative to dashboard cwd.
 */

import fs from "fs";
import path from "path";

export type UserProfileRow = {
  user_id: string;
  guild_id: string;
  username: string;
  display_name: string;
  avatar_url: string;
  joined_at: string;
  message_count: number;
  personality_summary: string;
  interests: string;
  notes: string;
  last_seen: string;
};

export type MemoryMessage = {
  id: number;
  message_id: string;
  guild_id: string;
  channel_id: string;
  channel_name: string;
  user_id: string;
  username: string;
  content: string;
  timestamp: string;
};

function resolveDbPath(): string {
  const candidates = [
    process.env.JAMIE_DB_PATH,
    path.join(process.cwd(), "..", "data", "jamie.db"),
    path.join(process.cwd(), "data", "jamie.db"),
    path.join(process.cwd(), "..", "..", "data", "jamie.db"),
  ].filter(Boolean) as string[];

  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return candidates[0] || path.join(process.cwd(), "..", "data", "jamie.db");
}

type Stmt = {
  all: (...params: unknown[]) => Record<string, unknown>[];
  get: (...params: unknown[]) => Record<string, unknown> | undefined;
  run: (...params: unknown[]) => { changes: number };
};

type DbSync = {
  prepare: (sql: string) => Stmt;
  exec: (sql: string) => void;
  close: () => void;
};

function openDb(opts?: { mustExist?: boolean }) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { DatabaseSync } = eval("require")("node:sqlite") as {
    DatabaseSync: new (path: string, opts?: { readOnly?: boolean }) => DbSync;
  };

  const dbPath = resolveDbPath();
  if (!fs.existsSync(dbPath)) {
    if (opts?.mustExist === false) {
      fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    } else {
      throw new Error(
        `Jamie database not found at ${dbPath}. Run the Discord bot first so data/jamie.db exists.`
      );
    }
  }

  const db = new DatabaseSync(dbPath);
  return { db, dbPath };
}

function ensureWelcomeTable(db: DbSync) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS welcome_config (
      guild_id       INTEGER PRIMARY KEY,
      enabled        INTEGER DEFAULT 0,
      channel_id     INTEGER,
      message        TEXT DEFAULT 'Welcome {user} — you are now Certified.',
      image_line     TEXT DEFAULT 'is now Certified',
      show_avatar    INTEGER DEFAULT 0,
      dm_on_join     INTEGER DEFAULT 0,
      background_path TEXT DEFAULT ''
    );
  `);
}

export type WelcomeConfig = {
  guild_id: string;
  enabled: boolean;
  channel_id: string | null;
  message: string;
  image_line: string;
  dm_on_join: boolean;
  background_path: string;
};

const WELCOME_DEFAULTS = {
  enabled: false,
  channel_id: null as string | null,
  message: "Welcome {user} — you are now Certified.",
  image_line: "is now Certified",
  dm_on_join: false,
  background_path: "",
};

function mapWelcome(row: Record<string, unknown> | undefined, guildId: string): WelcomeConfig {
  if (!row) {
    return { guild_id: String(guildId), ...WELCOME_DEFAULTS };
  }
  return {
    guild_id: String(row.guild_id ?? guildId),
    enabled: Boolean(Number(row.enabled ?? 0)),
    channel_id: row.channel_id != null && row.channel_id !== "" ? String(row.channel_id) : null,
    message: String(row.message ?? WELCOME_DEFAULTS.message),
    image_line: String(row.image_line ?? WELCOME_DEFAULTS.image_line),
    dm_on_join: Boolean(Number(row.dm_on_join ?? 0)),
    background_path: String(row.background_path ?? ""),
  };
}

export function getWelcomeConfig(guildId: string): WelcomeConfig {
  const { db } = openDb();
  try {
    ensureWelcomeTable(db);
    const row = db
      .prepare(
        `SELECT CAST(guild_id AS TEXT) as guild_id,
                enabled,
                CAST(channel_id AS TEXT) as channel_id,
                message, image_line, dm_on_join, background_path
         FROM welcome_config WHERE CAST(guild_id AS TEXT) = ?`
      )
      .get(String(guildId));
    return mapWelcome(row, guildId);
  } finally {
    db.close();
  }
}

export function setWelcomeConfig(
  guildId: string,
  patch: Partial<Omit<WelcomeConfig, "guild_id">>
): WelcomeConfig {
  const { db } = openDb();
  try {
    ensureWelcomeTable(db);
    const current = mapWelcome(
      db
        .prepare(
          `SELECT CAST(guild_id AS TEXT) as guild_id,
                  enabled,
                  CAST(channel_id AS TEXT) as channel_id,
                  message, image_line, dm_on_join, background_path
           FROM welcome_config WHERE CAST(guild_id AS TEXT) = ?`
        )
        .get(String(guildId)),
      guildId
    );

    const next: WelcomeConfig = {
      guild_id: String(guildId),
      enabled: patch.enabled ?? current.enabled,
      channel_id:
        patch.channel_id !== undefined ? patch.channel_id : current.channel_id,
      message: patch.message ?? current.message,
      image_line: patch.image_line ?? current.image_line,
      dm_on_join: patch.dm_on_join ?? current.dm_on_join,
      background_path:
        patch.background_path !== undefined
          ? patch.background_path
          : current.background_path,
    };

    db.prepare(
      `INSERT INTO welcome_config
         (guild_id, enabled, channel_id, message, image_line, show_avatar, dm_on_join, background_path)
       VALUES (?, ?, ?, ?, ?, 0, ?, ?)
       ON CONFLICT(guild_id) DO UPDATE SET
         enabled = excluded.enabled,
         channel_id = excluded.channel_id,
         message = excluded.message,
         image_line = excluded.image_line,
         show_avatar = 0,
         dm_on_join = excluded.dm_on_join,
         background_path = excluded.background_path`
    ).run(
      String(guildId),
      next.enabled ? 1 : 0,
      next.channel_id ? String(next.channel_id) : null,
      next.message,
      next.image_line,
      next.dm_on_join ? 1 : 0,
      next.background_path || ""
    );

    return next;
  } finally {
    db.close();
  }
}

export function welcomeBgDir(): string {
  return path.join(path.dirname(resolveDbPath()), "welcome_bgs");
}

export type StarboardConfig = {
  guild_id: string;
  enabled: boolean;
  channel_id: string | null;
  min_stars: number;
};

const STARBOARD_DEFAULTS = {
  enabled: false,
  channel_id: null as string | null,
  min_stars: 3,
};

function mapStarboard(row: Record<string, unknown> | undefined, guildId: string): StarboardConfig {
  if (!row) {
    return { guild_id: String(guildId), ...STARBOARD_DEFAULTS };
  }
  return {
    guild_id: String(row.guild_id ?? guildId),
    enabled: Boolean(Number(row.enabled ?? 0)),
    channel_id: row.channel_id != null && row.channel_id !== "" ? String(row.channel_id) : null,
    min_stars: row.min_stars != null ? Number(row.min_stars) : STARBOARD_DEFAULTS.min_stars,
  };
}

export function getStarboardConfig(guildId: string): StarboardConfig {
  const { db } = openDb();
  try {
    db.exec(`
      CREATE TABLE IF NOT EXISTS starboard_config (
        guild_id   INTEGER PRIMARY KEY,
        enabled    INTEGER DEFAULT 0,
        channel_id INTEGER,
        min_stars  INTEGER DEFAULT 3
      );
    `);
    const row = db
      .prepare(
        `SELECT CAST(guild_id AS TEXT) as guild_id,
                enabled,
                CAST(channel_id AS TEXT) as channel_id,
                min_stars
         FROM starboard_config WHERE CAST(guild_id AS TEXT) = ?`
      )
      .get(String(guildId));
    return mapStarboard(row, guildId);
  } finally {
    db.close();
  }
}

export function setStarboardConfig(
  guildId: string,
  patch: Partial<Omit<StarboardConfig, "guild_id">>
): StarboardConfig {
  const { db } = openDb();
  try {
    db.exec(`
      CREATE TABLE IF NOT EXISTS starboard_config (
        guild_id   INTEGER PRIMARY KEY,
        enabled    INTEGER DEFAULT 0,
        channel_id INTEGER,
        min_stars  INTEGER DEFAULT 3
      );
    `);
    const current = getStarboardConfig(guildId);
    const next: StarboardConfig = {
      guild_id: String(guildId),
      enabled: patch.enabled ?? current.enabled,
      channel_id: patch.channel_id !== undefined ? patch.channel_id : current.channel_id,
      min_stars: patch.min_stars ?? current.min_stars,
    };

    db.prepare(
      `INSERT INTO starboard_config (guild_id, enabled, channel_id, min_stars)
       VALUES (?, ?, ?, ?)
       ON CONFLICT(guild_id) DO UPDATE SET
         enabled = excluded.enabled,
         channel_id = excluded.channel_id,
         min_stars = excluded.min_stars`
    ).run(
      String(guildId),
      next.enabled ? 1 : 0,
      next.channel_id ? String(next.channel_id) : null,
      next.min_stars
    );

    return next;
  } finally {
    db.close();
  }
}

function mapProfile(row: Record<string, unknown>): UserProfileRow {
  return {
    user_id: String(row.user_id ?? ""),
    guild_id: String(row.guild_id ?? ""),
    username: String(row.username ?? ""),
    display_name: String(row.display_name ?? row.username ?? ""),
    avatar_url: String(row.avatar_url ?? ""),
    joined_at: String(row.joined_at ?? ""),
    message_count: Number(row.message_count ?? 0),
    personality_summary: String(row.personality_summary ?? ""),
    interests: String(row.interests ?? ""),
    notes: String(row.notes ?? ""),
    last_seen: String(row.last_seen ?? ""),
  };
}

export function listProfiles(opts?: {
  guildId?: string;
  search?: string;
  limit?: number;
}): { profiles: UserProfileRow[]; dbPath: string; total: number } {
  const { db, dbPath } = openDb();
  try {
    const limit = Math.min(Math.max(opts?.limit ?? 200, 1), 500);
    let rows: Record<string, unknown>[];

    // Cast snowflakes to TEXT — JS can't hold Discord IDs as safe numbers
    const cols = `CAST(user_id AS TEXT) as user_id,
      CAST(guild_id AS TEXT) as guild_id,
      username, display_name, avatar_url, joined_at, message_count,
      personality_summary, interests, notes, last_seen`;

    if (opts?.guildId && opts?.search) {
      const q = `%${opts.search}%`;
      rows = db
        .prepare(
          `SELECT ${cols} FROM user_profiles
           WHERE CAST(guild_id AS TEXT) = ?
             AND (username LIKE ? OR display_name LIKE ? OR notes LIKE ? OR personality_summary LIKE ? OR interests LIKE ?)
           ORDER BY message_count DESC
           LIMIT ?`
        )
        .all(String(opts.guildId), q, q, q, q, q, limit);
    } else if (opts?.guildId) {
      rows = db
        .prepare(
          `SELECT ${cols} FROM user_profiles WHERE CAST(guild_id AS TEXT) = ? ORDER BY message_count DESC LIMIT ?`
        )
        .all(String(opts.guildId), limit);
    } else if (opts?.search) {
      const q = `%${opts.search}%`;
      rows = db
        .prepare(
          `SELECT ${cols} FROM user_profiles
           WHERE username LIKE ? OR display_name LIKE ? OR notes LIKE ? OR personality_summary LIKE ? OR interests LIKE ?
           ORDER BY message_count DESC
           LIMIT ?`
        )
        .all(q, q, q, q, q, limit);
    } else {
      rows = db
        .prepare(
          `SELECT ${cols} FROM user_profiles ORDER BY message_count DESC LIMIT ?`
        )
        .all(limit);
    }

    const countRow = opts?.guildId
      ? db
          .prepare(
            `SELECT COUNT(*) as c FROM user_profiles WHERE CAST(guild_id AS TEXT) = ?`
          )
          .get(String(opts.guildId))
      : db.prepare(`SELECT COUNT(*) as c FROM user_profiles`).get();

    return {
      profiles: rows.map(mapProfile),
      dbPath,
      total: Number((countRow as { c?: number })?.c ?? rows.length),
    };
  } finally {
    db.close();
  }
}

export function getProfile(
  guildId: string,
  userId: string
): {
  profile: UserProfileRow | null;
  messages: MemoryMessage[];
  dbPath: string;
} {
  const { db, dbPath } = openDb();
  try {
    const cols = `CAST(user_id AS TEXT) as user_id,
      CAST(guild_id AS TEXT) as guild_id,
      username, display_name, avatar_url, joined_at, message_count,
      personality_summary, interests, notes, last_seen`;

    const row = db
      .prepare(
        `SELECT ${cols} FROM user_profiles
         WHERE CAST(guild_id AS TEXT) = ? AND CAST(user_id AS TEXT) = ?`
      )
      .get(String(guildId), String(userId));

    const msgs = db
      .prepare(
        `SELECT id,
           CAST(message_id AS TEXT) as message_id,
           CAST(guild_id AS TEXT) as guild_id,
           CAST(channel_id AS TEXT) as channel_id,
           channel_name,
           CAST(user_id AS TEXT) as user_id,
           username, content, timestamp
         FROM message_memory
         WHERE CAST(guild_id AS TEXT) = ? AND CAST(user_id AS TEXT) = ?
         ORDER BY timestamp DESC
         LIMIT 40`
      )
      .all(String(guildId), String(userId));

    return {
      profile: row ? mapProfile(row) : null,
      messages: msgs.map((m) => ({
        id: Number(m.id ?? 0),
        message_id: String(m.message_id ?? ""),
        guild_id: String(m.guild_id ?? ""),
        channel_id: String(m.channel_id ?? ""),
        channel_name: String(m.channel_name ?? ""),
        user_id: String(m.user_id ?? ""),
        username: String(m.username ?? ""),
        content: String(m.content ?? ""),
        timestamp: String(m.timestamp ?? ""),
      })),
      dbPath,
    };
  } finally {
    db.close();
  }
}

export function listGuildIdsFromProfiles(): string[] {
  const { db } = openDb();
  try {
    const rows = db
      .prepare(
        `SELECT DISTINCT CAST(guild_id AS TEXT) as guild_id FROM user_profiles ORDER BY guild_id`
      )
      .all();
    return rows.map((r) => String(r.guild_id));
  } finally {
    db.close();
  }
}

export function getGuildCommandsConfig(guildId: string): Record<string, boolean> {
  const { db } = openDb();
  try {
    db.exec(`
      CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id    INTEGER PRIMARY KEY,
        prefix      TEXT DEFAULT '?',
        modules_json TEXT DEFAULT '{}',
        commands_json TEXT DEFAULT '{}',
        custom_cmds_json TEXT DEFAULT '[]',
        muted_role_id INTEGER,
        log_channel_id INTEGER
      );
    `);
    const row = db
      .prepare("SELECT commands_json FROM guild_settings WHERE CAST(guild_id AS TEXT) = ?")
      .get(String(guildId)) as { commands_json: string } | undefined;
    if (row && row.commands_json) {
      try {
        return JSON.parse(row.commands_json);
      } catch {
        return {};
      }
    }
    return {};
  } finally {
    db.close();
  }
}

export function setGuildCommandsConfig(guildId: string, config: Record<string, boolean>): Record<string, boolean> {
  const { db } = openDb();
  try {
    db.exec(`
      CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id    INTEGER PRIMARY KEY,
        prefix      TEXT DEFAULT '?',
        modules_json TEXT DEFAULT '{}',
        commands_json TEXT DEFAULT '{}',
        custom_cmds_json TEXT DEFAULT '[]',
        muted_role_id INTEGER,
        log_channel_id INTEGER
      );
    `);
    const row = db
      .prepare("SELECT commands_json FROM guild_settings WHERE CAST(guild_id AS TEXT) = ?")
      .get(String(guildId)) as { commands_json: string } | undefined;
    
    let existing = {};
    if (row && row.commands_json) {
      try {
        existing = JSON.parse(row.commands_json);
      } catch {}
    }
    const merged = { ...existing, ...config };
    const serialized = JSON.stringify(merged);

    db.prepare(`
      INSERT INTO guild_settings (guild_id, commands_json)
      VALUES (?, ?)
      ON CONFLICT(guild_id) DO UPDATE SET commands_json = excluded.commands_json
    `).run(String(guildId), serialized);

    return merged;
  } finally {
    db.close();
  }
}
