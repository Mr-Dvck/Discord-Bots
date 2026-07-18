/**
 * Dashboard tools — full Discord admin surface for Jamie chat operator.
 * Prefer named tools; use discord_request for anything else Discord's API supports.
 */

import {
  getGuilds,
  getGuild,
  getGuildChannels,
  getGuildRoles,
  getGuildMembers,
  createChannel,
  deleteChannel,
  createRole,
  deleteRole,
  modifyRole,
  createCategory,
  modifyChannel,
  sendMessage,
  getMessages,
  deleteMessage,
  bulkDeleteMessages,
  pinMessage,
  createInvite,
  addRoleToMember,
  removeRoleFromMember,
  modifyMember,
  kickMember,
  banMember,
  unbanMember,
  editChannelPermissions,
  deleteChannelPermission,
  discordRequest,
  buildServer,
  type ServerBlueprint,
} from "@/lib/discord";
import {
  getWelcomeConfig,
  setWelcomeConfig,
  getStarboardConfig,
  setStarboardConfig,
} from "@/lib/jamie-db";

/** Local blueprint generator to avoid circular import with llm.ts */
async function generateServerBlueprint(description: string): Promise<string> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = process.env.JAMIE_LLM_MODEL || "meta-llama/llama-3.3-70b-instruct";
  const apiBase = process.env.JAMIE_LLM_API_BASE || "https://openrouter.ai/api/v1";
  if (!apiKey) throw new Error("OPENROUTER_API_KEY not set");

  const prompt = `Based on this description, generate a Discord server structure as JSON:
"${description}"

Output ONLY valid JSON in this exact format:
{
  "categories": [
    {
      "name": "Category Name",
      "channels": [
        {"name": "channel-name", "type": "text", "topic": "Channel description"},
        {"name": "voice-chat", "type": "voice"}
      ]
    }
  ],
  "roles": [
    {"name": "Role Name", "color": "#FF0000", "hoist": true}
  ]
}

Be creative and thorough. Include at least 4-5 categories with appropriate channels. Use lowercase with hyphens for channel names.`;

  const res = await fetch(`${apiBase}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: "You are a Discord server architect. Output only valid JSON." },
        { role: "user", content: prompt },
      ],
      temperature: 0.8,
      max_tokens: 1000,
    }),
    cache: "no-store",
  });

  if (!res.ok) throw new Error(`LLM API ${res.status}`);
  const data = await res.json();
  return data.choices[0].message.content;
}

export type ToolName =
  | "list_guilds"
  | "get_server"
  | "list_channels"
  | "list_roles"
  | "list_members"
  | "create_category"
  | "create_channel"
  | "delete_channel"
  | "modify_channel"
  | "create_role"
  | "delete_role"
  | "modify_role"
  | "assign_role"
  | "remove_role"
  | "set_nickname"
  | "timeout_member"
  | "kick_member"
  | "ban_member"
  | "unban_member"
  | "send_message"
  | "get_messages"
  | "delete_message"
  | "bulk_delete_messages"
  | "pin_message"
  | "create_invite"
  | "set_channel_permission"
  | "clear_channel_permission"
  | "setup_counting_game"
  | "generate_image"
  | "generate_blueprint"
  | "build_server"
  | "discord_request"
  | "get_welcome_config"
  | "set_welcome_config"
  | "get_starboard_config"
  | "set_starboard_config"
  | "join_voice_channel"
  | "leave_voice_channel";

export interface ToolCall {
  id: string;
  name: ToolName;
  arguments: Record<string, unknown>;
}

export interface PendingAction {
  id: string;
  tool: ToolName;
  args: Record<string, unknown>;
  summary: string;
  destructive: boolean;
}

export interface ExecutedAction {
  id: string;
  tool: ToolName;
  summary: string;
  ok: boolean;
  result?: unknown;
  error?: string;
}

/** Tools that must not run until the user confirms in the UI. */
export const DESTRUCTIVE_TOOLS: Set<ToolName> = new Set([
  "delete_channel",
  "delete_role",
  "kick_member",
  "ban_member",
  "bulk_delete_messages",
  "build_server",
]);

const CHANNEL_TYPE_NAMES: Record<string, number> = {
  text: 0,
  voice: 2,
  category: 4,
  stage: 13,
  forum: 15,
};

const GUILD_SCOPED = new Set<ToolName>([
  "get_server",
  "list_channels",
  "list_roles",
  "list_members",
  "create_category",
  "create_channel",
  "create_role",
  "delete_role",
  "modify_role",
  "assign_role",
  "remove_role",
  "set_nickname",
  "timeout_member",
  "kick_member",
  "ban_member",
  "unban_member",
  "setup_counting_game",
  "build_server",
]);

export function toolNeedsGuildId(name: string): boolean {
  return GUILD_SCOPED.has(name as ToolName);
}

function tool(
  name: ToolName,
  description: string,
  properties: Record<string, unknown>,
  required: string[] = []
) {
  return {
    type: "function" as const,
    function: {
      name,
      description,
      parameters: {
        type: "object",
        properties,
        required,
        additionalProperties: false,
      },
    },
  };
}

export const DASHBOARD_TOOLS = [
  tool("list_guilds", "List Discord servers the bot is in.", {}),
  tool(
    "get_server",
    "Get basic info for a server.",
    { guild_id: { type: "string" } },
    ["guild_id"]
  ),
  tool(
    "list_channels",
    "List all channels/categories. type 0=text 2=voice 4=category 13=stage 15=forum.",
    { guild_id: { type: "string" } },
    ["guild_id"]
  ),
  tool(
    "list_roles",
    "List server roles with ids, names, colors, positions.",
    { guild_id: { type: "string" } },
    ["guild_id"]
  ),
  tool(
    "list_members",
    "List members (up to limit, default 100). Needs Server Members Intent.",
    {
      guild_id: { type: "string" },
      limit: { type: "number", description: "1-1000" },
    },
    ["guild_id"]
  ),
  tool(
    "create_category",
    "Create a category (section).",
    { guild_id: { type: "string" }, name: { type: "string" } },
    ["guild_id", "name"]
  ),
  tool(
    "create_channel",
    "Create a channel. type: text|voice|forum|stage. parent_id = category id.",
    {
      guild_id: { type: "string" },
      name: { type: "string" },
      type: { type: "string", enum: ["text", "voice", "forum", "stage"] },
      parent_id: { type: "string" },
      topic: { type: "string" },
      nsfw: { type: "boolean" },
    },
    ["guild_id", "name"]
  ),
  tool(
    "modify_channel",
    "Edit channel name, topic, parent, position, nsfw.",
    {
      channel_id: { type: "string" },
      name: { type: "string" },
      topic: { type: "string" },
      parent_id: { type: "string", description: "Category id, or empty to clear" },
      position: { type: "number" },
      nsfw: { type: "boolean" },
    },
    ["channel_id"]
  ),
  tool(
    "delete_channel",
    "Delete a channel/category. DESTRUCTIVE — needs confirm.",
    {
      channel_id: { type: "string" },
      channel_name: { type: "string" },
    },
    ["channel_id"]
  ),
  tool(
    "create_role",
    "Create a role.",
    {
      guild_id: { type: "string" },
      name: { type: "string" },
      color: { type: "string", description: "#RRGGBB" },
      hoist: { type: "boolean" },
      mentionable: { type: "boolean" },
      permissions: { type: "string", description: "Permission bitfield as string" },
    },
    ["guild_id", "name"]
  ),
  tool(
    "modify_role",
    "Edit a role name/color/hoist/mentionable/permissions.",
    {
      guild_id: { type: "string" },
      role_id: { type: "string" },
      name: { type: "string" },
      color: { type: "string" },
      hoist: { type: "boolean" },
      mentionable: { type: "boolean" },
      permissions: { type: "string" },
    },
    ["guild_id", "role_id"]
  ),
  tool(
    "delete_role",
    "Delete a role. DESTRUCTIVE — needs confirm.",
    {
      guild_id: { type: "string" },
      role_id: { type: "string" },
      role_name: { type: "string" },
    },
    ["guild_id", "role_id"]
  ),
  tool(
    "assign_role",
    "Give a member a role.",
    {
      guild_id: { type: "string" },
      user_id: { type: "string" },
      role_id: { type: "string" },
    },
    ["guild_id", "user_id", "role_id"]
  ),
  tool(
    "remove_role",
    "Remove a role from a member.",
    {
      guild_id: { type: "string" },
      user_id: { type: "string" },
      role_id: { type: "string" },
    },
    ["guild_id", "user_id", "role_id"]
  ),
  tool(
    "set_nickname",
    "Set a member nickname (empty string clears).",
    {
      guild_id: { type: "string" },
      user_id: { type: "string" },
      nick: { type: "string" },
    },
    ["guild_id", "user_id", "nick"]
  ),
  tool(
    "timeout_member",
    "Timeout a member. duration_minutes 0 clears timeout. Max ~40320 (28d).",
    {
      guild_id: { type: "string" },
      user_id: { type: "string" },
      duration_minutes: { type: "number" },
      reason: { type: "string" },
    },
    ["guild_id", "user_id", "duration_minutes"]
  ),
  tool(
    "kick_member",
    "Kick a member. DESTRUCTIVE — needs confirm.",
    {
      guild_id: { type: "string" },
      user_id: { type: "string" },
      reason: { type: "string" },
    },
    ["guild_id", "user_id"]
  ),
  tool(
    "ban_member",
    "Ban a member. DESTRUCTIVE — needs confirm.",
    {
      guild_id: { type: "string" },
      user_id: { type: "string" },
      reason: { type: "string" },
      delete_message_seconds: { type: "number", description: "0-604800" },
    },
    ["guild_id", "user_id"]
  ),
  tool(
    "unban_member",
    "Unban a user by id.",
    { guild_id: { type: "string" }, user_id: { type: "string" } },
    ["guild_id", "user_id"]
  ),
  tool(
    "send_message",
    "Post a message as the bot. Optional simple embed title+description.",
    {
      channel_id: { type: "string" },
      content: { type: "string" },
      embed_title: { type: "string" },
      embed_description: { type: "string" },
    },
    ["channel_id"]
  ),
  tool(
    "get_messages",
    "Fetch recent messages in a channel.",
    {
      channel_id: { type: "string" },
      limit: { type: "number", description: "1-100" },
    },
    ["channel_id"]
  ),
  tool(
    "delete_message",
    "Delete one message.",
    {
      channel_id: { type: "string" },
      message_id: { type: "string" },
    },
    ["channel_id", "message_id"]
  ),
  tool(
    "bulk_delete_messages",
    "Bulk delete 2-100 messages under 14 days old. DESTRUCTIVE — needs confirm.",
    {
      channel_id: { type: "string" },
      message_ids: {
        type: "array",
        items: { type: "string" },
      },
    },
    ["channel_id", "message_ids"]
  ),
  tool(
    "pin_message",
    "Pin a message in a channel.",
    {
      channel_id: { type: "string" },
      message_id: { type: "string" },
    },
    ["channel_id", "message_id"]
  ),
  tool(
    "create_invite",
    "Create an invite for a channel.",
    {
      channel_id: { type: "string" },
      max_age: { type: "number", description: "Seconds, 0 = never" },
      max_uses: { type: "number" },
    },
    ["channel_id"]
  ),
  tool(
    "set_channel_permission",
    "Set overwrite for a role (type=0) or member (type=1). allow/deny are permission bit strings.",
    {
      channel_id: { type: "string" },
      overwrite_id: { type: "string", description: "Role or user id" },
      type: { type: "number", description: "0 role, 1 member" },
      allow: { type: "string" },
      deny: { type: "string" },
    },
    ["channel_id", "overwrite_id", "type"]
  ),
  tool(
    "clear_channel_permission",
    "Remove a permission overwrite.",
    {
      channel_id: { type: "string" },
      overwrite_id: { type: "string" },
    },
    ["channel_id", "overwrite_id"]
  ),
  tool(
    "setup_counting_game",
    "Create/enable a counting game channel (topic [jamie:counting]). Bot auto-moderates counts.",
    {
      guild_id: { type: "string" },
      parent_id: { type: "string", description: "Category id" },
      channel_name: { type: "string" },
      start: { type: "number" },
      channel_id: { type: "string", description: "Existing channel to convert" },
    },
    ["guild_id"]
  ),
  tool(
    "generate_image",
    "Generate an image (LLM enhance + Pollinations flux). " +
      "ONLY pass channel_id when the user gave a real Discord channel snowflake ID " +
      "(from list_channels). NEVER pass null, \"null\", or invent an ID. " +
      "If no channel, omit channel_id — generate only and tell them to open Image Studio or name a channel. " +
      "size: square|welcome|banner|portrait|story. For join banners, generate BACKGROUND ART only (no names/text); " +
      "Welcome module stamps member names on join.",
    {
      prompt: { type: "string", description: "What to generate (art only — no baked-in names)" },
      size: {
        type: "string",
        enum: ["square", "welcome", "banner", "portrait", "story"],
      },
      enhance: { type: "boolean", description: "LLM enhance prompt (default true)" },
      channel_id: {
        type: "string",
        description:
          "Optional real channel snowflake from list_channels. Omit entirely if not posting.",
      },
      caption: { type: "string" },
    },
    ["prompt"]
  ),
  tool(
    "generate_blueprint",
    "AI-generate a server blueprint JSON from a description (does not apply).",
    { description: { type: "string" } },
    ["description"]
  ),
  tool(
    "build_server",
    "Apply a full blueprint. DESTRUCTIVE/high impact — needs confirm.",
    {
      guild_id: { type: "string" },
      blueprint: { type: "object" },
    },
    ["guild_id", "blueprint"]
  ),
  tool(
    "discord_request",
    "ESCAPE HATCH: raw Discord REST under /api/v10. Use when no named tool fits. " +
      "method GET|POST|PATCH|PUT|DELETE, path like /guilds/{id}/channels, optional JSON body. " +
      "Examples: create webhook POST /channels/{id}/webhooks; edit guild PATCH /guilds/{id}. " +
      "Never invent IDs. Prefer named tools when available.",
    {
      method: { type: "string", enum: ["GET", "POST", "PATCH", "PUT", "DELETE"] },
      path: { type: "string", description: "Must start with /" },
      body: { type: "object", description: "JSON body for POST/PATCH/PUT" },
    },
    ["method", "path"]
  ),
  tool(
    "get_welcome_config",
    "Get the welcome module configuration (enabled state, channel, message, dm_on_join) for a server.",
    { guild_id: { type: "string" } },
    ["guild_id"]
  ),
  tool(
    "set_welcome_config",
    "Set/update the welcome module configuration for a server.",
    {
      guild_id: { type: "string" },
      enabled: { type: "boolean" },
      channel_id: { type: "string", description: "Channel snowflake ID to post welcome messages, or null to clear" },
      message: { type: "string", description: "Welcome message template, supports {user}, {server}, {membercount}" },
      dm_on_join: { type: "boolean", description: "Whether to also DM the welcome message on join" },
    },
    ["guild_id"]
  ),
  tool(
    "get_starboard_config",
    "Get the starboard module configuration (enabled state, channel, min_stars) for a server.",
    { guild_id: { type: "string" } },
    ["guild_id"]
  ),
  tool(
    "set_starboard_config",
    "Set/update the starboard module configuration for a server.",
    {
      guild_id: { type: "string" },
      enabled: { type: "boolean" },
      channel_id: { type: "string", description: "Channel snowflake ID to post starboard embed logs, or null to clear" },
      min_stars: { type: "number", description: "Minimum star (⭐) reactions required to post, default 3" },
    },
    ["guild_id"]
  ),
  tool(
    "join_voice_channel",
    "Join a voice channel with the bot.",
    {
      guild_id: { type: "string" },
      channel_id: { type: "string" },
    },
    ["guild_id", "channel_id"]
  ),
  tool(
    "leave_voice_channel",
    "Leave the current voice channel in a server.",
    {
      guild_id: { type: "string" },
    },
    ["guild_id"]
  ),
];

function str(v: unknown, fallback = ""): string {
  if (typeof v === "string") {
    const s = v.trim();
    // Models often pass the literal words "null" / "undefined"
    if (!s || s === "null" || s === "undefined" || s === "None" || s === "none") {
      return fallback;
    }
    return s;
  }
  if (typeof v === "number" && Number.isFinite(v)) return String(Math.trunc(v));
  return fallback;
}

/** Discord snowflake only — rejects "null", empty, non-numeric junk. */
function snowflake(v: unknown): string {
  const s = str(v);
  if (!s) return "";
  if (!/^\d{5,22}$/.test(s)) return "";
  return s;
}

function bool(v: unknown, fallback = false): boolean {
  return typeof v === "boolean" ? v : fallback;
}

function num(v: unknown, fallback = 0): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

export function summarizeTool(name: ToolName, args: Record<string, unknown>): string {
  switch (name) {
    case "list_guilds":
      return "List servers Jamie is in";
    case "get_server":
      return `Get server ${str(args.guild_id)}`;
    case "list_channels":
      return `List channels on ${str(args.guild_id)}`;
    case "list_roles":
      return `List roles on ${str(args.guild_id)}`;
    case "list_members":
      return `List members on ${str(args.guild_id)}`;
    case "create_category":
      return `Create category "${str(args.name)}"`;
    case "create_channel":
      return `Create ${str(args.type, "text")} channel #${str(args.name)}`;
    case "modify_channel":
      return `Modify channel ${str(args.channel_id)}`;
    case "delete_channel":
      return `Delete channel ${str(args.channel_name) || str(args.channel_id)}`;
    case "create_role":
      return `Create role "${str(args.name)}"`;
    case "modify_role":
      return `Modify role ${str(args.role_id)}`;
    case "delete_role":
      return `Delete role ${str(args.role_name) || str(args.role_id)}`;
    case "assign_role":
      return `Assign role ${str(args.role_id)} → user ${str(args.user_id)}`;
    case "remove_role":
      return `Remove role ${str(args.role_id)} from ${str(args.user_id)}`;
    case "set_nickname":
      return `Nick ${str(args.user_id)} → ${str(args.nick)}`;
    case "timeout_member":
      return `Timeout ${str(args.user_id)} ${num(args.duration_minutes)}m`;
    case "kick_member":
      return `Kick ${str(args.user_id)}`;
    case "ban_member":
      return `Ban ${str(args.user_id)}`;
    case "unban_member":
      return `Unban ${str(args.user_id)}`;
    case "send_message":
      return `Send message in ${str(args.channel_id)}`;
    case "get_messages":
      return `Get messages in ${str(args.channel_id)}`;
    case "delete_message":
      return `Delete message ${str(args.message_id)}`;
    case "bulk_delete_messages":
      return `Bulk delete in ${str(args.channel_id)}`;
    case "pin_message":
      return `Pin ${str(args.message_id)}`;
    case "create_invite":
      return `Create invite for ${str(args.channel_id)}`;
    case "set_channel_permission":
      return `Perms on ${str(args.channel_id)} for ${str(args.overwrite_id)}`;
    case "clear_channel_permission":
      return `Clear perms ${str(args.overwrite_id)} on ${str(args.channel_id)}`;
    case "setup_counting_game":
      return `Setup counting #${str(args.channel_name, "counting")}`;
    case "generate_image":
      return `Generate image: ${str(args.prompt).slice(0, 60)}`;
    case "generate_blueprint":
      return `Generate blueprint: ${str(args.description).slice(0, 80)}`;
    case "build_server": {
      const bp = args.blueprint as ServerBlueprint | undefined;
      return `Build server (${bp?.categories?.length ?? 0} cats, ${bp?.roles?.length ?? 0} roles)`;
    }
    case "discord_request":
      return `${str(args.method, "GET").toUpperCase()} ${str(args.path)}`;
    default:
      return String(name);
  }
}

function parseBlueprintJson(raw: string): ServerBlueprint | null {
  try {
    const start = raw.indexOf("{");
    const end = raw.lastIndexOf("}") + 1;
    if (start < 0 || end <= start) return null;
    const parsed = JSON.parse(raw.slice(start, end));
    if (!parsed || !Array.isArray(parsed.categories) || !Array.isArray(parsed.roles)) {
      return null;
    }
    return parsed as ServerBlueprint;
  } catch {
    return null;
  }
}

function slimResult(data: unknown, max = 4000): unknown {
  try {
    const s = JSON.stringify(data);
    if (s.length <= max) return data;
    return { truncated: true, preview: s.slice(0, max) };
  } catch {
    return data;
  }
}

export async function executeTool(
  name: ToolName,
  args: Record<string, unknown>
): Promise<{ ok: boolean; result?: unknown; error?: string }> {
  try {
    switch (name) {
      case "list_guilds": {
        const guilds = await getGuilds();
        const slim = (Array.isArray(guilds) ? guilds : []).map(
          (g: { id: string; name: string; member_count?: number }) => ({
            id: g.id,
            name: g.name,
            member_count: g.member_count ?? null,
          })
        );
        return { ok: true, result: slim };
      }

      case "get_server": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const guild = await getGuild(guildId);
        return {
          ok: true,
          result: {
            id: guild.id,
            name: guild.name,
            member_count:
              guild.approximate_member_count ?? guild.member_count ?? null,
          },
        };
      }

      case "list_channels": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const channels = await getGuildChannels(guildId);
        const slim = (Array.isArray(channels) ? channels : [])
          .sort(
            (a: { position: number }, b: { position: number }) =>
              a.position - b.position
          )
          .map(
            (c: {
              id: string;
              name: string;
              type: number;
              parent_id: string | null;
              topic?: string | null;
              position?: number;
            }) => ({
              id: c.id,
              name: c.name,
              type: c.type,
              parent_id: c.parent_id,
              topic: c.topic || undefined,
              position: c.position,
            })
          );
        return { ok: true, result: slim };
      }

      case "list_roles": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const roles = await getGuildRoles(guildId);
        const slim = (Array.isArray(roles) ? roles : [])
          .sort(
            (a: { position: number }, b: { position: number }) =>
              b.position - a.position
          )
          .map(
            (r: {
              id: string;
              name: string;
              color: number;
              hoist: boolean;
              permissions?: string;
              position: number;
            }) => ({
              id: r.id,
              name: r.name,
              color: r.color,
              hoist: r.hoist,
              permissions: r.permissions,
              position: r.position,
            })
          );
        return { ok: true, result: slim };
      }

      case "list_members": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        let limit = Math.floor(num(args.limit, 100));
        if (limit < 1) limit = 100;
        if (limit > 1000) limit = 1000;
        const members = await getGuildMembers(guildId, limit);
        const slim = (Array.isArray(members) ? members : []).map(
          (m: {
            user?: { id: string; username: string; bot?: boolean };
            nick?: string | null;
            roles?: string[];
          }) => ({
            id: m.user?.id,
            username: m.user?.username,
            nick: m.nick,
            bot: m.user?.bot ?? false,
            roles: m.roles,
          })
        );
        return { ok: true, result: slim };
      }

      case "create_category": {
        const guildId = str(args.guild_id);
        const name = str(args.name);
        if (!guildId || !name) return { ok: false, error: "guild_id and name required" };
        const created = await createCategory(guildId, name);
        return {
          ok: true,
          result: { id: created.id, name: created.name, type: created.type },
        };
      }

      case "create_channel": {
        const guildId = str(args.guild_id);
        const name = str(args.name);
        if (!guildId || !name) return { ok: false, error: "guild_id and name required" };
        const typeKey = str(args.type, "text").toLowerCase();
        const type = CHANNEL_TYPE_NAMES[typeKey] ?? 0;
        const parent_id = str(args.parent_id) || undefined;
        const topic = str(args.topic) || undefined;
        const nsfw = bool(args.nsfw, false);
        const created = await createChannel(guildId, {
          name,
          type,
          parent_id,
          topic,
          nsfw,
        });
        return {
          ok: true,
          result: {
            id: created.id,
            name: created.name,
            type: created.type,
            parent_id: created.parent_id,
            topic: created.topic,
          },
        };
      }

      case "modify_channel": {
        const channelId = str(args.channel_id);
        if (!channelId) return { ok: false, error: "channel_id required" };
        const data: Record<string, unknown> = {};
        if (args.name !== undefined) data.name = str(args.name);
        if (args.topic !== undefined) data.topic = str(args.topic);
        if (args.position !== undefined) data.position = num(args.position);
        if (args.nsfw !== undefined) data.nsfw = bool(args.nsfw);
        if (args.parent_id !== undefined) {
          const p = str(args.parent_id);
          data.parent_id = p === "" ? null : p;
        }
        const updated = await modifyChannel(channelId, data as {
          name?: string;
          topic?: string;
          position?: number;
          parent_id?: string | null;
        });
        return {
          ok: true,
          result: {
            id: updated?.id ?? channelId,
            name: updated?.name,
            topic: updated?.topic,
            parent_id: updated?.parent_id,
          },
        };
      }

      case "delete_channel": {
        const channelId = str(args.channel_id);
        if (!channelId) return { ok: false, error: "channel_id required" };
        await deleteChannel(channelId);
        return {
          ok: true,
          result: { deleted: channelId, name: str(args.channel_name) || null },
        };
      }

      case "create_role": {
        const guildId = str(args.guild_id);
        const name = str(args.name);
        if (!guildId || !name) return { ok: false, error: "guild_id and name required" };
        const colorHex = str(args.color).replace("#", "");
        const color = colorHex ? parseInt(colorHex, 16) : 0;
        const created = await createRole(guildId, {
          name,
          color: Number.isFinite(color) ? color : 0,
          hoist: bool(args.hoist, false),
          mentionable: bool(args.mentionable, false),
          permissions: str(args.permissions) || undefined,
        });
        return {
          ok: true,
          result: { id: created.id, name: created.name, color: created.color },
        };
      }

      case "modify_role": {
        const guildId = str(args.guild_id);
        const roleId = str(args.role_id);
        if (!guildId || !roleId) return { ok: false, error: "guild_id and role_id required" };
        const data: {
          name?: string;
          color?: number;
          hoist?: boolean;
          mentionable?: boolean;
          permissions?: string;
        } = {};
        if (args.name !== undefined) data.name = str(args.name);
        if (args.color !== undefined) {
          const hex = str(args.color).replace("#", "");
          const c = parseInt(hex, 16);
          if (Number.isFinite(c)) data.color = c;
        }
        if (args.hoist !== undefined) data.hoist = bool(args.hoist);
        if (args.mentionable !== undefined) data.mentionable = bool(args.mentionable);
        if (args.permissions !== undefined) data.permissions = str(args.permissions);
        const updated = await modifyRole(guildId, roleId, data);
        return { ok: true, result: { id: updated?.id ?? roleId, name: updated?.name } };
      }

      case "delete_role": {
        const guildId = str(args.guild_id);
        const roleId = str(args.role_id);
        if (!guildId || !roleId) {
          return { ok: false, error: "guild_id and role_id required" };
        }
        await deleteRole(guildId, roleId);
        return {
          ok: true,
          result: { deleted: roleId, name: str(args.role_name) || null },
        };
      }

      case "assign_role": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        const roleId = str(args.role_id);
        if (!guildId || !userId || !roleId) {
          return { ok: false, error: "guild_id, user_id, role_id required" };
        }
        await addRoleToMember(guildId, userId, roleId);
        return { ok: true, result: { guild_id: guildId, user_id: userId, role_id: roleId } };
      }

      case "remove_role": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        const roleId = str(args.role_id);
        if (!guildId || !userId || !roleId) {
          return { ok: false, error: "guild_id, user_id, role_id required" };
        }
        await removeRoleFromMember(guildId, userId, roleId);
        return { ok: true, result: { guild_id: guildId, user_id: userId, role_id: roleId } };
      }

      case "set_nickname": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        if (!guildId || !userId) return { ok: false, error: "guild_id and user_id required" };
        const nick = str(args.nick);
        await modifyMember(guildId, userId, { nick: nick || null });
        return { ok: true, result: { user_id: userId, nick: nick || null } };
      }

      case "timeout_member": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        if (!guildId || !userId) return { ok: false, error: "guild_id and user_id required" };
        let mins = Math.floor(num(args.duration_minutes, 0));
        if (mins < 0) mins = 0;
        if (mins > 40320) mins = 40320;
        const until =
          mins === 0
            ? null
            : new Date(Date.now() + mins * 60_000).toISOString();
        await modifyMember(guildId, userId, {
          communication_disabled_until: until,
        });
        return { ok: true, result: { user_id: userId, until, minutes: mins } };
      }

      case "kick_member": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        if (!guildId || !userId) return { ok: false, error: "guild_id and user_id required" };
        await kickMember(guildId, userId, str(args.reason) || undefined);
        return { ok: true, result: { kicked: userId } };
      }

      case "ban_member": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        if (!guildId || !userId) return { ok: false, error: "guild_id and user_id required" };
        let del = Math.floor(num(args.delete_message_seconds, 0));
        if (del < 0) del = 0;
        if (del > 604800) del = 604800;
        await banMember(guildId, userId, {
          delete_message_seconds: del,
          reason: str(args.reason) || undefined,
        });
        return { ok: true, result: { banned: userId } };
      }

      case "unban_member": {
        const guildId = str(args.guild_id);
        const userId = str(args.user_id);
        if (!guildId || !userId) return { ok: false, error: "guild_id and user_id required" };
        await unbanMember(guildId, userId);
        return { ok: true, result: { unbanned: userId } };
      }

      case "send_message": {
        const channelId = str(args.channel_id);
        let content = str(args.content);
        const embedTitle = str(args.embed_title) || "🔥 Jamie";
        const embedDesc = str(args.embed_description) || content;
        if (!channelId) return { ok: false, error: "channel_id required" };
        if (!embedDesc && !content) {
          return { ok: false, error: "content or embed required" };
        }
        if (embedDesc.length > 4096) {
          // sendMessage wraps content as embed; pass description chunks via first embed only
        }
        const embeds = [
          {
            title: embedTitle,
            description: (embedDesc || content).slice(0, 4096),
            color: 0x39b7c4,
          },
        ];
        // content empty → pure embed message
        const msg = await sendMessage(channelId, "", embeds);
        return {
          ok: true,
          result: { id: msg?.id, channel_id: channelId, embedded: true },
        };
      }

      case "get_messages": {
        const channelId = str(args.channel_id);
        if (!channelId) return { ok: false, error: "channel_id required" };
        let limit = Math.floor(num(args.limit, 50));
        if (limit < 1) limit = 1;
        if (limit > 100) limit = 100;
        const messages = await getMessages(channelId, limit);
        const slim = (Array.isArray(messages) ? messages : []).map(
          (m: {
            id: string;
            content?: string;
            author?: { id: string; username: string };
          }) => ({
            id: m.id,
            content: (m.content || "").slice(0, 300),
            author: m.author?.username,
            author_id: m.author?.id,
          })
        );
        return { ok: true, result: slim };
      }

      case "delete_message": {
        const channelId = str(args.channel_id);
        const messageId = str(args.message_id);
        if (!channelId || !messageId) {
          return { ok: false, error: "channel_id and message_id required" };
        }
        await deleteMessage(channelId, messageId);
        return { ok: true, result: { deleted: messageId } };
      }

      case "bulk_delete_messages": {
        const channelId = str(args.channel_id);
        const ids = Array.isArray(args.message_ids)
          ? args.message_ids.map((x) => String(x)).filter(Boolean)
          : [];
        if (!channelId || ids.length < 2) {
          return { ok: false, error: "channel_id and 2+ message_ids required" };
        }
        await bulkDeleteMessages(channelId, ids.slice(0, 100));
        return { ok: true, result: { deleted_count: Math.min(ids.length, 100) } };
      }

      case "pin_message": {
        const channelId = str(args.channel_id);
        const messageId = str(args.message_id);
        if (!channelId || !messageId) {
          return { ok: false, error: "channel_id and message_id required" };
        }
        await pinMessage(channelId, messageId);
        return { ok: true, result: { pinned: messageId } };
      }

      case "create_invite": {
        const channelId = str(args.channel_id);
        if (!channelId) return { ok: false, error: "channel_id required" };
        const inv = await createInvite(channelId, {
          max_age: num(args.max_age, 0),
          max_uses: num(args.max_uses, 0) || undefined,
        });
        return {
          ok: true,
          result: {
            code: inv?.code,
            url: inv?.code ? `https://discord.gg/${inv.code}` : null,
          },
        };
      }

      case "set_channel_permission": {
        const channelId = str(args.channel_id);
        const overwriteId = str(args.overwrite_id);
        const type = num(args.type, 0) as 0 | 1;
        if (!channelId || !overwriteId) {
          return { ok: false, error: "channel_id and overwrite_id required" };
        }
        await editChannelPermissions(channelId, overwriteId, {
          type: type === 1 ? 1 : 0,
          allow: str(args.allow, "0"),
          deny: str(args.deny, "0"),
        });
        return { ok: true, result: { channel_id: channelId, overwrite_id: overwriteId } };
      }

      case "clear_channel_permission": {
        const channelId = str(args.channel_id);
        const overwriteId = str(args.overwrite_id);
        if (!channelId || !overwriteId) {
          return { ok: false, error: "channel_id and overwrite_id required" };
        }
        await deleteChannelPermission(channelId, overwriteId);
        return { ok: true, result: { cleared: overwriteId } };
      }

      case "setup_counting_game": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const startNum = Math.max(1, Math.floor(num(args.start, 1)));
        const topic = `[jamie:counting start=${startNum}] Count up from ${startNum}. One number per message. No double counts.`;
        const existingId = str(args.channel_id);
        let channel: { id: string; name: string; parent_id?: string | null; topic?: string };

        if (existingId) {
          const updated = await modifyChannel(existingId, { topic });
          channel = {
            id: updated?.id ?? existingId,
            name: updated?.name ?? existingId,
            parent_id: updated?.parent_id,
            topic: updated?.topic ?? topic,
          };
        } else {
          // Plain ascii slug first; createChannel applies bold unicode
          const channelName =
            str(args.channel_name, "counting")
              .toLowerCase()
              .replace(/\s+/g, "-")
              .replace(/[^a-z0-9\-_]/g, "")
              .slice(0, 90) || "counting";
          const parentId = str(args.parent_id) || undefined;
          const created = await createChannel(guildId, {
            name: channelName,
            type: 0,
            parent_id: parentId,
            topic,
          });
          channel = {
            id: created.id,
            name: created.name,
            parent_id: created.parent_id,
            topic: created.topic ?? topic,
          };
        }

        const rules =
          `**Counting game is live.**\n` +
          `• Post the next number only (starting at **${startNum}**)\n` +
          `• One count per person — no double-taps\n` +
          `• Wrong number resets to **${startNum}**\n` +
          `Jamie runs this channel automatically.`;
        try {
          await sendMessage(channel.id, rules);
        } catch {
          /* ignore */
        }

        return {
          ok: true,
          result: {
            channel_id: channel.id,
            channel_name: channel.name,
            parent_id: channel.parent_id ?? null,
            topic: channel.topic,
            start: startNum,
          },
        };
      }

      case "generate_image": {
        const prompt = str(args.prompt);
        if (!prompt) return { ok: false, error: "prompt required" };
        const { generateImage, IMAGE_SIZES } = await import("@/lib/image");
        const sizeKey = str(args.size, "welcome");
        const size = (
          sizeKey in IMAGE_SIZES ? sizeKey : "welcome"
        ) as keyof typeof IMAGE_SIZES;
        const enhance = args.enhance !== false;
        const img = await generateImage({ prompt, size, enhance });

        // Only post when we have a real Discord snowflake (never "null"/junk)
        const channelId = snowflake(args.channel_id);
        let posted: { id?: string } | null = null;
        let postError: string | null = null;

        if (args.channel_id != null && args.channel_id !== "" && !channelId) {
          postError =
            "channel_id was missing or invalid (got null/non-snowflake). Image was still generated — name a real channel from list_channels to post.";
        } else if (channelId) {
          const token = process.env.DISCORD_BOT_TOKEN_JAMIE;
          if (!token) {
            postError = "No bot token to post";
          } else {
            const bytes = Buffer.from(img.base64, "base64");
            const form = new FormData();
            form.append(
              "files[0]",
              new Blob([new Uint8Array(bytes)], { type: "image/png" }),
              "jamie_gen.png"
            );
            form.append(
              "payload_json",
              JSON.stringify({
                content: `🎨 ${str(args.caption) || prompt}`.slice(0, 1900),
              })
            );
            const res = await fetch(
              `https://discord.com/api/v10/channels/${channelId}/messages`,
              {
                method: "POST",
                headers: { Authorization: `Bot ${token}` },
                body: form,
                cache: "no-store",
              }
            );
            if (res.ok) {
              const msg = await res.json();
              posted = { id: msg.id };
            } else {
              const err = await res.text();
              postError = `Discord post failed: ${err.slice(0, 180)}`;
            }
          }
        }

        // Generation succeeded even if post was skipped/failed — don't fail the whole tool
        return {
          ok: true,
          result: {
            generated: true,
            prompt,
            enhancedPrompt: img.enhancedPrompt,
            size: `${img.width}x${img.height}`,
            // Intentionally no base64/dataUrl — keeps chat context small; use Image Studio to view/download
            posted: Boolean(posted),
            message_id: posted?.id ?? null,
            channel_id: channelId || null,
            post_error: postError,
            note: posted
              ? "Image posted to Discord channel."
              : postError
                ? `Image generated. Not posted: ${postError}`
                : "Image generated (not posted). Open Image Studio to download, or name a #channel (I'll list_channels for the ID) to post it.",
          },
        };
      }

      case "generate_blueprint": {
        const description = str(args.description);
        if (!description) return { ok: false, error: "description required" };
        const raw = await generateServerBlueprint(description);
        const blueprint = parseBlueprintJson(raw);
        if (!blueprint) {
          return {
            ok: false,
            error: "Could not parse blueprint JSON from model",
            result: { raw: raw.slice(0, 500) },
          };
        }
        return { ok: true, result: { blueprint, raw } };
      }

      case "build_server": {
        const guildId = str(args.guild_id);
        const blueprint = args.blueprint as ServerBlueprint;
        if (!guildId || !blueprint) {
          return { ok: false, error: "guild_id and blueprint required" };
        }
        if (!Array.isArray(blueprint.categories) || !Array.isArray(blueprint.roles)) {
          return { ok: false, error: "blueprint must include categories[] and roles[]" };
        }
        const results = await buildServer(guildId, blueprint);
        return { ok: true, result: results };
      }

      case "discord_request": {
        const method = str(args.method, "GET").toUpperCase();
        const path = str(args.path);
        if (!path) return { ok: false, error: "path required" };
        // DELETE via escape hatch still runs when confirmed or if not in DESTRUCTIVE set
        // Mark DELETE for pending only when allowDestructive false — handled by caller via DESTRUCTIVE_TOOLS
        // Actually DELETE is not always in DESTRUCTIVE_TOOLS for discord_request - we should treat DELETE method as needing confirm
        const body = args.body && typeof args.body === "object" ? args.body : undefined;
        const result = await discordRequest(method, path, body);
        return { ok: true, result: slimResult(result) };
      }

      case "get_welcome_config": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const config = getWelcomeConfig(guildId);
        return { ok: true, result: config };
      }

      case "set_welcome_config": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const patch: any = {};
        if (typeof args.enabled === "boolean") patch.enabled = args.enabled;
        if (args.channel_id !== undefined) patch.channel_id = args.channel_id;
        if (typeof args.message === "string") patch.message = args.message;
        if (typeof args.dm_on_join === "boolean") patch.dm_on_join = args.dm_on_join;
        const config = setWelcomeConfig(guildId, patch);
        return { ok: true, result: config };
      }

      case "get_starboard_config": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const config = getStarboardConfig(guildId);
        return { ok: true, result: config };
      }

      case "set_starboard_config": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        const patch: any = {};
        if (typeof args.enabled === "boolean") patch.enabled = args.enabled;
        if (args.channel_id !== undefined) patch.channel_id = args.channel_id;
        if (typeof args.min_stars === "number") patch.min_stars = args.min_stars;
        const config = setStarboardConfig(guildId, patch);
        return { ok: true, result: config };
      }

      case "join_voice_channel": {
        const guildId = str(args.guild_id);
        const channelId = str(args.channel_id);
        if (!guildId || !channelId) {
          return { ok: false, error: "guild_id and channel_id required" };
        }
        // Use discord_request to join voice channel via Discord API
        const result = await discordRequest("POST", `/guilds/${guildId}/voice-states/@me`, {
          channel_id: channelId,
        });
        return { ok: true, result: { joined: channelId, guild_id: guildId } };
      }

      case "leave_voice_channel": {
        const guildId = str(args.guild_id);
        if (!guildId) return { ok: false, error: "guild_id required" };
        // Use discord_request to leave voice channel via Discord API
        const result = await discordRequest("DELETE", `/guilds/${guildId}/voice-states/@me`);
        return { ok: true, result: { left: guildId } };
      }

      default:
        return { ok: false, error: `Unknown tool: ${name}` };
    }
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return { ok: false, error: message };
  }
}

/** True if this tool call should require UI confirmation. */
export function isDestructiveCall(name: ToolName, args: Record<string, unknown>): boolean {
  if (DESTRUCTIVE_TOOLS.has(name)) return true;
  if (name === "discord_request") {
    const method = str(args.method, "GET").toUpperCase();
    return method === "DELETE";
  }
  return false;
}
