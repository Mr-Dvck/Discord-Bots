/**
 * Jamie slash command catalog (mirrors the bot command packs).
 */

export interface SlashCommand {
  name: string;
  group?: string;
  full: string;
  description: string;
  pack: string;
  category: string;
}

export const COMMAND_PACKS = [
  "Core",
  "Manage",
  "Moderation",
  "Mod Logs",
] as const;

function cmd(
  name: string,
  description: string,
  pack: string,
  category: string,
  group?: string
): SlashCommand {
  return {
    name,
    group,
    full: group ? `/${group} ${name}` : `/${name}`,
    description,
    pack,
    category,
  };
}

export const SLASH_COMMANDS: SlashCommand[] = [
  // ── Core Jamie ────────────────────────────────────────────────
  // ── Core Jamie Commands (chat, memory, images, voice) ─────────
  cmd("talk", "Talk to Jamie directly", "Core", "Chat"),
  cmd("ask", "Ask about someone/something", "Core", "Chat"),
  cmd("rant", "Long rant about a topic (+ praise or − roast), up to 4000 chars", "Core", "Chat"),
  cmd("generate", "Generate an image", "Core", "Images"),
  cmd("imagine", "Jamie imagines something wild", "Core", "Images"),
  cmd("profile", "View Jamie's profile on a user", "Core", "Memory"),
  cmd("servermap", "View the server map", "Core", "Memory"),
  cmd("remember", "Search Jamie's message memory", "Core", "Memory"),
  cmd("note", "Add a profile note to a user (admin)", "Core", "Memory"),
  cmd("stats", "View server memory statistics", "Core", "Memory"),
  cmd("join", "Join a voice channel", "Core", "Voice"),
  cmd("leave", "Leave the current voice channel", "Core", "Voice"),

  // ── Manage (manage_cmds.py) ───────────────────────────────────
  cmd("addmod", "Add a moderator role", "Manage", "Roles", "manage"),
  cmd("delmod", "Remove a moderator role", "Manage", "Roles", "manage"),
  cmd("listmods", "List moderators", "Manage", "Roles", "manage"),
  cmd("addrole", "Add a new role, with optional color and hoist", "Manage", "Roles", "manage"),
  cmd("delrole", "Delete a role", "Manage", "Roles", "manage"),
  cmd("rolecolor", "Change the color of a role", "Manage", "Roles", "manage"),
  cmd("rolename", "Change the name of a role", "Manage", "Roles", "manage"),
  cmd("mentionable", "Toggle making a role mentionable on/off", "Manage", "Roles", "manage"),
  cmd("role", "Add/remove a user to a role", "Manage", "Roles", "manage"),
  cmd("nick", "Change the bot nickname", "Manage", "Server", "manage"),
  cmd("setnick", "Change the nickname of a user", "Manage", "Server", "manage"),
  cmd("purge", "Delete a number of messages from a channel", "Manage", "Messages", "manage"),
  cmd("announce", "Send an announcement using the bot", "Manage", "Messages", "manage"),
  cmd("modules", "List available modules", "Manage", "Config", "manage"),
  cmd("module", "Enable/disable a module", "Manage", "Config", "manage"),
  cmd("command", "Enable/disable a command", "Manage", "Config", "manage"),
  cmd("prefix", "Get or set the command prefix", "Manage", "Config", "manage"),
  cmd("ignorechannel", "Toggle command usage in a channel", "Manage", "Ignores", "manage"),
  cmd("ignoreuser", "Toggle command usage for a user", "Manage", "Ignores", "manage"),
  cmd("ignorerole", "Toggle command usage for a role", "Manage", "Ignores", "manage"),
  cmd("clearwarn", "Clear warnings for a user", "Manage", "Moderation", "manage"),
  cmd("customs", "List custom commands", "Manage", "Config", "manage"),
  cmd("addemote", "Add an emote to the server", "Manage", "Server", "manage"),

  // ── Moderation (mod_cmds.py) ──────────────────────────────────
  cmd("kick", "Kick a member", "Moderation", "Actions", "mod"),
  cmd("ban", "Ban a member (optional time limit)", "Moderation", "Actions", "mod"),
  cmd("softban", "Ban and immediate unban to delete user messages", "Moderation", "Actions", "mod"),
  cmd("unban", "Unban a member", "Moderation", "Actions", "mod"),
  cmd("mute", "Mute a member so they cannot type", "Moderation", "Actions", "mod"),
  cmd("unmute", "Unmute a member", "Moderation", "Actions", "mod"),
  cmd("deafen", "Deafen a member", "Moderation", "Voice", "mod"),
  cmd("undeafen", "Undeafen a member", "Moderation", "Voice", "mod"),
  cmd("warn", "Warn a member", "Moderation", "Actions", "mod"),
  cmd("clean", "Clean up bot responses", "Moderation", "Messages", "mod"),
  cmd("members", "List members in a role (max 90)", "Moderation", "Info", "mod"),
  cmd("diagnose", "Diagnose any command or module for problems", "Moderation", "Info", "mod"),
  cmd("rolepersist", "Assign/unassign a role that persists on rejoin", "Moderation", "Roles", "mod"),
  cmd("temprole", "Assign a temporary role", "Moderation", "Roles", "mod"),
  cmd("lock", "Lock a channel with optional timer", "Moderation", "Channels", "mod"),
  cmd("unlock", "Unlock a previously locked channel", "Moderation", "Channels", "mod"),
  cmd("lockdown", "Lock channels in the current category", "Moderation", "Channels", "mod"),
  cmd("ignored", "List ignored users, roles, and channels", "Moderation", "Info", "mod"),
  cmd("moderations", "Get a list of active timed moderations", "Moderation", "Info", "mod"),
  cmd("duration", "Change the duration of a mute/ban case", "Moderation", "Cases", "mod"),
  cmd("star", "View starboard stats for a message", "Moderation", "Info", "mod"),

  // ── Mod Logs (modlog_cmds.py) ─────────────────────────────────
  cmd("modlogs", "Get moderation logs for a user", "Mod Logs", "Cases", "modlog"),
  cmd("case", "Show a single mod log case", "Mod Logs", "Cases", "modlog"),
  cmd("reason", "Supply a reason for a mod log case", "Mod Logs", "Cases", "modlog"),
  cmd("warnings", "Get warnings for a user", "Mod Logs", "Warnings", "modlog"),
  cmd("delwarn", "Delete a warning", "Mod Logs", "Warnings", "modlog"),
  cmd("note", "Add note(s) about a member", "Mod Logs", "Notes", "modlog"),
  cmd("notes", "Get notes for a user", "Mod Logs", "Notes", "modlog"),
  cmd("delnote", "Delete a note about a member", "Mod Logs", "Notes", "modlog"),
  cmd("clearnotes", "Delete all notes for a member", "Mod Logs", "Notes", "modlog"),
  cmd("editnote", "Edit a note about a member", "Mod Logs", "Notes", "modlog"),
  cmd("modstats", "Get moderation statistics for a mod/admin", "Mod Logs", "Info", "modlog"),
];

export function commandsByPack(): Record<string, SlashCommand[]> {
  const map: Record<string, SlashCommand[]> = {};
  for (const c of SLASH_COMMANDS) {
    if (!map[c.pack]) map[c.pack] = [];
    map[c.pack].push(c);
  }
  return map;
}
