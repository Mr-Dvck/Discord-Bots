/**
 * Discord API client — server-side only (uses bot token)
 */

const DISCORD_API = "https://discord.com/api/v10";

async function discordFetch(path: string, method: string = "GET", body?: unknown) {
  const token = process.env.DISCORD_BOT_TOKEN_JAMIE;
  if (!token) throw new Error("DISCORD_BOT_TOKEN_JAMIE not set");

  const res = await fetch(`${DISCORD_API}${path}`, {
    method,
    headers: {
      Authorization: `Bot ${token}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Discord API ${res.status}: ${err.slice(0, 200)}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ── Guild operations ──────────────────────────────────────────────

export async function getGuilds() {
  // with_counts adds approximate_member_count / approximate_presence_count
  const guilds = await discordFetch("/users/@me/guilds?with_counts=true&limit=200");
  if (!Array.isArray(guilds)) return guilds;

  return guilds.map((g: Record<string, unknown>) => ({
    ...g,
    member_count:
      (g.approximate_member_count as number | undefined) ??
      (g.member_count as number | undefined),
  }));
}

export async function getGuild(guildId: string) {
  return discordFetch(`/guilds/${guildId}?with_counts=true`);
}

export async function getGuildChannels(guildId: string) {
  return discordFetch(`/guilds/${guildId}/channels`);
}

export async function getGuildRoles(guildId: string) {
  return discordFetch(`/guilds/${guildId}/roles`);
}

export async function getGuildMembers(guildId: string, limit: number = 100) {
  return discordFetch(`/guilds/${guildId}/members?limit=${limit}`);
}

// ── Channel operations ────────────────────────────────────────────

export async function createChannel(guildId: string, data: {
  name: string;
  type?: number; // 0=text, 2=voice, 4=category, 13=stage, 15=forum
  parent_id?: string;
  topic?: string;
  nsfw?: boolean;
  position?: number;
}) {
  return discordFetch(`/guilds/${guildId}/channels`, "POST", data);
}

export async function modifyChannel(channelId: string, data: {
  name?: string;
  topic?: string;
  position?: number;
  parent_id?: string | null;
}) {
  return discordFetch(`/channels/${channelId}`, "PATCH", data);
}

export async function deleteChannel(channelId: string) {
  return discordFetch(`/channels/${channelId}`, "DELETE");
}

// ── Role operations ────────────────────────────────────────────────

export async function createRole(guildId: string, data: {
  name: string;
  color?: number;
  hoist?: boolean;
  permissions?: string;
  mentionable?: boolean;
}) {
  return discordFetch(`/guilds/${guildId}/roles`, "POST", data);
}

export async function modifyRole(guildId: string, roleId: string, data: {
  name?: string;
  color?: number;
  permissions?: string;
  hoist?: boolean;
  mentionable?: boolean;
}) {
  return discordFetch(`/guilds/${guildId}/roles/${roleId}`, "PATCH", data);
}

export async function deleteRole(guildId: string, roleId: string) {
  return discordFetch(`/guilds/${guildId}/roles/${roleId}`, "DELETE");
}

// ── Member operations ─────────────────────────────────────────────

export async function addRoleToMember(guildId: string, userId: string, roleId: string) {
  return discordFetch(`/guilds/${guildId}/members/${userId}/roles/${roleId}`, "PUT");
}

export async function removeRoleFromMember(guildId: string, userId: string, roleId: string) {
  return discordFetch(`/guilds/${guildId}/members/${userId}/roles/${roleId}`, "DELETE");
}

export async function modifyMember(
  guildId: string,
  userId: string,
  data: {
    nick?: string | null;
    roles?: string[];
    mute?: boolean;
    deaf?: boolean;
    channel_id?: string | null;
    communication_disabled_until?: string | null;
  }
) {
  return discordFetch(`/guilds/${guildId}/members/${userId}`, "PATCH", data);
}

export async function kickMember(guildId: string, userId: string, reason?: string) {
  const q = reason ? `?reason=${encodeURIComponent(reason)}` : "";
  // Discord expects reason header; pass via body-less DELETE with X-Audit-Log-Reason via fetch override
  const token = process.env.DISCORD_BOT_TOKEN_JAMIE;
  if (!token) throw new Error("DISCORD_BOT_TOKEN_JAMIE not set");
  const res = await fetch(`https://discord.com/api/v10/guilds/${guildId}/members/${userId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bot ${token}`,
      ...(reason ? { "X-Audit-Log-Reason": reason.slice(0, 512) } : {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Discord API ${res.status}: ${err.slice(0, 200)}`);
  }
  return null;
}

export async function banMember(
  guildId: string,
  userId: string,
  data?: { delete_message_seconds?: number; reason?: string }
) {
  const token = process.env.DISCORD_BOT_TOKEN_JAMIE;
  if (!token) throw new Error("DISCORD_BOT_TOKEN_JAMIE not set");
  const res = await fetch(`https://discord.com/api/v10/guilds/${guildId}/bans/${userId}`, {
    method: "PUT",
    headers: {
      Authorization: `Bot ${token}`,
      "Content-Type": "application/json",
      ...(data?.reason ? { "X-Audit-Log-Reason": data.reason.slice(0, 512) } : {}),
    },
    body: JSON.stringify({
      delete_message_seconds: data?.delete_message_seconds ?? 0,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Discord API ${res.status}: ${err.slice(0, 200)}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export async function unbanMember(guildId: string, userId: string) {
  return discordFetch(`/guilds/${guildId}/bans/${userId}`, "DELETE");
}

// ── Message operations ────────────────────────────────────────────

export async function sendMessage(
  channelId: string,
  content: string,
  embeds?: unknown[]
) {
  return discordFetch(`/channels/${channelId}/messages`, "POST", {
    content: content || undefined,
    embeds: embeds?.length ? embeds : undefined,
  });
}

export async function getMessages(channelId: string, limit: number = 50) {
  return discordFetch(`/channels/${channelId}/messages?limit=${limit}`);
}

export async function deleteMessage(channelId: string, messageId: string) {
  return discordFetch(`/channels/${channelId}/messages/${messageId}`, "DELETE");
}

export async function bulkDeleteMessages(channelId: string, messageIds: string[]) {
  return discordFetch(`/channels/${channelId}/messages/bulk-delete`, "POST", {
    messages: messageIds,
  });
}

export async function pinMessage(channelId: string, messageId: string) {
  return discordFetch(`/channels/${channelId}/pins/${messageId}`, "PUT");
}

export async function createInvite(
  channelId: string,
  data?: { max_age?: number; max_uses?: number; temporary?: boolean; unique?: boolean }
) {
  return discordFetch(`/channels/${channelId}/invites`, "POST", data ?? { max_age: 0 });
}

export async function editChannelPermissions(
  channelId: string,
  overwriteId: string,
  data: { type: 0 | 1; allow?: string; deny?: string }
) {
  // type 0 = role, 1 = member
  return discordFetch(`/channels/${channelId}/permissions/${overwriteId}`, "PUT", data);
}

export async function deleteChannelPermission(channelId: string, overwriteId: string) {
  return discordFetch(`/channels/${channelId}/permissions/${overwriteId}`, "DELETE");
}

/**
 * Escape hatch: arbitrary Discord REST call under /api/v10.
 * path must start with / and must not include scheme/host.
 */
export async function discordRequest(
  method: string,
  path: string,
  body?: unknown
) {
  const m = method.toUpperCase();
  if (!["GET", "POST", "PATCH", "PUT", "DELETE"].includes(m)) {
    throw new Error(`Unsupported method ${method}`);
  }
  let p = path.trim();
  if (!p.startsWith("/")) p = `/${p}`;
  if (p.includes("://") || p.includes("..")) {
    throw new Error("Invalid path");
  }
  return discordFetch(p, m, body);
}

// ── Category helper ────────────────────────────────────────────────

export async function createCategory(guildId: string, name: string) {
  return discordFetch(`/guilds/${guildId}/channels`, "POST", {
    name,
    type: 4, // category
  });
}

// ── Bulk server build ─────────────────────────────────────────────

export interface ServerBlueprint {
  categories: {
    name: string;
    channels: {
      name: string;
      type: "text" | "voice" | "forum" | "stage";
      topic?: string;
      nsfw?: boolean;
    }[];
  }[];
  roles: {
    name: string;
    color?: string;
    hoist?: boolean;
    permissions?: string;
  }[];
}

const CHANNEL_TYPE_MAP: Record<string, number> = {
  text: 0,
  voice: 2,
  forum: 15,
  stage: 13,
};

export async function buildServer(guildId: string, blueprint: ServerBlueprint) {
  const results: { roles: any[]; channels: any[]; errors: string[] } = {
    roles: [],
    channels: [],
    errors: [],
  };

  // Create roles first
  for (const role of blueprint.roles) {
    try {
      const colorNum = role.color ? parseInt(role.color.replace("#", ""), 16) : 0;
      const created = await createRole(guildId, {
        name: role.name,
        color: colorNum,
        hoist: role.hoist ?? false,
        permissions: role.permissions ?? "0",
      });
      results.roles.push(created);
    } catch (e: any) {
      results.errors.push(`Role "${role.name}": ${e.message}`);
    }
  }

  // Create categories and their channels
  for (const cat of blueprint.categories) {
    try {
      const category = await createCategory(guildId, cat.name);
      results.channels.push(category);

      // Create channels under this category
      for (const ch of cat.channels) {
        try {
          const channel = await createChannel(guildId, {
            name: ch.name,
            type: CHANNEL_TYPE_MAP[ch.type] ?? 0,
            parent_id: category.id,
            topic: ch.topic ?? "",
            nsfw: ch.nsfw ?? false,
          });
          results.channels.push(channel);
        } catch (e: any) {
          results.errors.push(`Channel "${ch.name}": ${e.message}`);
        }
      }
    } catch (e: any) {
      results.errors.push(`Category "${cat.name}": ${e.message}`);
    }
  }

  return results;
}
