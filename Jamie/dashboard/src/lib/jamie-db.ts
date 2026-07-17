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

function openDb() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { DatabaseSync } = require("node:sqlite") as {
    DatabaseSync: new (path: string, opts?: { readOnly?: boolean }) => {
      prepare: (sql: string) => {
        all: (...params: unknown[]) => Record<string, unknown>[];
        get: (...params: unknown[]) => Record<string, unknown> | undefined;
      };
      close: () => void;
    };
  };

  const dbPath = resolveDbPath();
  if (!fs.existsSync(dbPath)) {
    throw new Error(
      `Jamie database not found at ${dbPath}. Run the Discord bot and talk in-server so memory is written.`
    );
  }

  // readOnly may fail if file locked for write by bot — open normal and only SELECT
  const db = new DatabaseSync(dbPath);
  return { db, dbPath };
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
