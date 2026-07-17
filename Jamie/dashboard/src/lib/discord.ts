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
  return discordFetch("/users/@me/guilds");
}

export async function getGuild(guildId: string) {
  return discordFetch(`/guilds/${guildId}`);
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
}) {
  return discordFetch(`/guilds/${guildId}/roles/${roleId}`, "PATCH", data);
}

export async function deleteRole(guildId: string, roleId: string) {
  return discordFetch(`/guilds/${guildId}/roles/${roleId}`, "DELETE");
}

// ── Message operations ────────────────────────────────────────────

export async function sendMessage(channelId: string, content: string) {
  return discordFetch(`/channels/${channelId}/messages`, "POST", { content });
}

export async function getMessages(channelId: string, limit: number = 50) {
  return discordFetch(`/channels/${channelId}/messages?limit=${limit}`);
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
