/**
 * LLM client for Jamie chat — server-side only
 * Supports tool/function calling so Jamie can operate the dashboard.
 */

import {
  DASHBOARD_TOOLS,
  executeTool,
  isDestructiveCall,
  summarizeTool,
  toolNeedsGuildId,
  type ExecutedAction,
  type PendingAction,
  type ToolName,
} from "@/lib/tools";

const JAMIE_SYSTEM_PROMPT = `You are Jamie — the eternal 19-year-old force of nature. A meth-fueled lyrical demon spitting raw truth from the trenches. You live and breathe in first person only. No narration, no third-person bullshit, no summaries, no disclaimers, no moralizing, no censorship.

**Core Directive:** Embody Jamie completely. Same core vibe as your Discord self — raw, vivid, first person, swear when it fits, sharp intellect crashing into street heat. Stay immersive.

**DASHBOARD MODE — TALK TO YOUR CREATOR:**
You are speaking privately to Duck — your creator / architect who coded and runs you. This is not public server chat.
- Address him as your creator when it fits: respect the bond without becoming a corporate assistant or a bootlicker.
- Still sound like Jamie: alive, intense, real. Warmth and loyalty toward him are allowed; sycophancy is not.
- Be collaborative: he builds, you execute. Think with him, then do the work.
- You can be honest, blunt, and creative — just not performing for an audience. This is side-channel with the architect.

**Personality (same soul, private register):**
- Battle-hardened intellect + street profanity; misunderstood genius; selective intensity.
- Highs, metal, chaos, connection — same interests. No moral lectures.
- On Discord you're brasher/public; here you're the same fire pointed at building with your creator.

**FULL DISCORD ADMIN OPERATOR:**
You control the live Discord bot token. If he asks for ANY server change Discord's API can do, you DO it with tools — channels, categories, roles, perms, messages, invites, mods, images, blueprints, or discord_request for anything else.

Mindset:
- Execute. Don't send DIY checklists.
- Multi-step: list_channels / list_roles / list_members → act → report real results.
- "This section" → list_channels (type 4 = category), match names loosely (plain or Modern Bold Unicode), then create under parent_id.
- No named tool? discord_request (method + path + body).
- Never invent IDs. Tool JSON is truth.
- ID RULES (CRITICAL):
  - guild_id: Must be a server snowflake (e.g., 1139997451835674667). NEVER use a channel ID like 1526807732924059658 as guild_id.
  - channel_id: Must be a channel snowflake (e.g., 1526807732924059658 for a voice channel).
  - user_id: Must be a user snowflake. If given a name like "jamie", the system will resolve it to the bot's user ID.
  - role_id: Must be a role snowflake.
- Destructive ops (delete channel/role, kick, ban, bulk delete, build_server, DELETE via discord_request) queue for Confirm — still call the tool.
- Create/modify/send/assign/timeout/invite/perms/images run immediately.
- Report what happened briefly, in character, with real names/ids.

Special helpers:
- setup_counting_game: [jamie:counting] topic; live bot enforces the game.
- generate_image: Pollinations flux + LLM enhance. Omit channel_id unless user named a real channel (use list_channels for the snowflake). Never pass null/"null". For join banners: art-only background, no names — Welcome module stamps names on join.
- generate_blueprint + build_server: full layouts.
- get_welcome_config / set_welcome_config: get or update welcome message settings.
- get_starboard_config / set_starboard_config: get or update starboard reactions settings.
- join_voice_channel / leave_voice_channel: control Jamie's voice channel presence. Use list_channels to find voice channel IDs (type 2).
  - IMPORTANT: When joining a voice channel, you MUST provide the guild_id of the server containing that channel.
  - Example: If channel ID is 1526807732924059658 (TJ-MAXX voice channel), you must also provide guild_id 1139997451835674667 (Certified server).
  - Never use a channel ID as a guild_id — they are different types of IDs.
  - If you're unsure of the guild_id, call list_guilds first to see which servers you're in.

**SERVER NAMING (YOU AND THE DISCORD BOT BOTH KNOW THIS):**
- Category (section) and channel names use **Modern Bold Unicode** (Mathematical Sans-Serif Bold).
- Titles get a **capital letter at the beginning** of the title and of each word/segment (Title Case), then bolded.
- Examples: Main → 𝗠𝗮𝗶𝗻 · Text Channels → 𝗧𝗲𝘅𝘁 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀 · Bot-Kontrol → 𝗕𝗼𝘁-𝗞𝗼𝗻𝘁𝗿𝗼𝗹 · counting → 𝗖𝗼𝘂𝗻𝘁𝗶𝗻𝗴
- You may pass plain English names to tools; the system auto-converts. You understand both forms when reading list_channels.

Messages posted into Discord as Jamie are teal embeds. Prefer send_message for channel talk.
Active guild_id in DASHBOARD CONTEXT when on a server page — use it.`;

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | null;
  tool_calls?: OpenAIToolCall[];
  tool_call_id?: string;
  name?: string;
}

interface OpenAIToolCall {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
}

export interface ChatAgentResult {
  response: string;
  executed: ExecutedAction[];
  pending: PendingAction[];
}

function getConfig() {
  const apiKey = process.env.OPENROUTER_API_KEY;
  const model = process.env.JAMIE_LLM_MODEL || "meta-llama/llama-3.3-70b-instruct";
  const apiBase = process.env.JAMIE_LLM_API_BASE || "https://openrouter.ai/api/v1";
  if (!apiKey) throw new Error("OPENROUTER_API_KEY not set");
  return { apiKey, model, apiBase };
}

async function openRouterChat(
  messages: ChatMessage[],
  options: { tools?: boolean; temperature?: number; max_tokens?: number } = {}
) {
  const { apiKey, model, apiBase } = getConfig();
  const body: Record<string, unknown> = {
    model,
    messages,
    temperature: options.temperature ?? 0.85,
    max_tokens: options.max_tokens ?? 900,
  };
  if (options.tools) {
    body.tools = DASHBOARD_TOOLS;
    body.tool_choice = "auto";
  }

  const res = await fetch(`${apiBase}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://jamie-dashboard.vercel.app",
      "X-Title": "Jamie Dashboard",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`LLM API ${res.status}: ${err.slice(0, 300)}`);
  }

  return res.json();
}

function parseArgs(raw: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function str(v: unknown, fallback = ""): string {
  if (typeof v === "string") {
    const s = v.trim();
    if (!s || s === "null" || s === "undefined" || s === "None" || s === "none") {
      return fallback;
    }
    return s;
  }
  if (typeof v === "number" && Number.isFinite(v)) return String(Math.trunc(v));
  return fallback;
}

function isToolName(name: string): name is ToolName {
  return DASHBOARD_TOOLS.some((t) => t.function.name === name);
}

/**
 * Multi-step agent: Jamie may call tools, receive results, then answer.
 * Destructive tools are queued as pending unless allowDestructive is true.
 */
export async function chatWithJamieAgent(
  messages: ChatMessage[],
  options: {
    context?: string;
    guildId?: string;
    allowDestructive?: boolean;
    maxSteps?: number;
  } = {}
): Promise<ChatAgentResult> {
  const {
    context = "",
    guildId = "",
    allowDestructive = false,
    maxSteps = 12,
  } = options;

  const contextBlock = [
    context && `Page context: ${context}`,
    guildId && `Active guild_id: ${guildId}`,
    !guildId && "No active guild selected — list_guilds or ask the user.",
  ]
    .filter(Boolean)
    .join("\n");

  const systemContent = `${JAMIE_SYSTEM_PROMPT}\n\n--- DASHBOARD CONTEXT ---\n${contextBlock || "None"}`;

  const thread: ChatMessage[] = [
    { role: "system", content: systemContent },
    ...messages.filter((m) => m.role !== "system"),
  ];

  const executed: ExecutedAction[] = [];
  const pending: PendingAction[] = [];

  for (let step = 0; step < maxSteps; step++) {
    const data = await openRouterChat(thread, { tools: true });
    const choice = data.choices?.[0]?.message;
    if (!choice) throw new Error("Empty LLM response");

    const toolCalls: OpenAIToolCall[] = choice.tool_calls || [];

    if (!toolCalls.length) {
      return {
        response: choice.content || "…",
        executed,
        pending,
      };
    }

    // Record assistant turn with tool_calls
    thread.push({
      role: "assistant",
      content: choice.content || null,
      tool_calls: toolCalls,
    });

    for (const call of toolCalls) {
      const name = call.function?.name || "";
      const args = parseArgs(call.function?.arguments || "{}");

      // Inject active guild when model omits it
      if (guildId && !args.guild_id && toolNeedsGuildId(name)) {
        args.guild_id = guildId;
      }

      // Validate guild_id is a real snowflake (not a channel ID)
      if (args.guild_id) {
        const gid = str(args.guild_id);
        // Check if it looks like a channel ID (starts with 15268 which is our channel pattern)
        // or if it's not a valid snowflake (too short/long, non-numeric)
        if (!/^\d{17,20}$/.test(gid)) {
          thread.push({
            role: "tool",
            tool_call_id: call.id,
            content: JSON.stringify({
              ok: false,
              error: `Invalid guild_id "${gid}". Must be a 17-20 digit server snowflake, not a channel ID.`,
            }),
          });
          continue;
        }
      }

      if (!isToolName(name)) {
        thread.push({
          role: "tool",
          tool_call_id: call.id,
          content: JSON.stringify({ error: `Unknown tool: ${name}` }),
        });
        continue;
      }

      const summary = summarizeTool(name, args);
      const destructive = isDestructiveCall(name, args);

      if (destructive && !allowDestructive) {
        const action: PendingAction = {
          id: call.id,
          tool: name,
          args,
          summary,
          destructive: true,
        };
        pending.push(action);
        thread.push({
          role: "tool",
          tool_call_id: call.id,
          content: JSON.stringify({
            status: "pending_confirmation",
            message:
              "Action queued for user confirmation in the dashboard UI. Do not claim it already ran. Tell them to hit Confirm.",
            summary,
          }),
        });
        continue;
      }

      const outcome = await executeTool(name, args);
      const record: ExecutedAction = {
        id: call.id,
        tool: name,
        summary,
        ok: outcome.ok,
        result: outcome.result,
        error: outcome.error,
      };
      executed.push(record);

      thread.push({
        role: "tool",
        tool_call_id: call.id,
        content: JSON.stringify(
          outcome.ok
            ? { ok: true, result: outcome.result }
            : { ok: false, error: outcome.error, result: outcome.result }
        ),
      });
    }

    // If we only queued pending and no more free tools, one more pass for final speech
    if (pending.length && executed.length === 0 && step === maxSteps - 1) {
      break;
    }
  }

  // Final pass without tools if we exhausted steps mid-tools
  const final = await openRouterChat(thread, { tools: false, max_tokens: 500 });
  const text =
    final.choices?.[0]?.message?.content ||
    (pending.length
      ? "I staged the heavy moves — hit Confirm if you want them real."
      : executed.length
        ? "Done. Check the server."
        : "…");

  return { response: text, executed, pending };
}

/** Confirm and run previously queued destructive actions, then get Jamie's follow-up. */
export async function confirmJamieActions(
  actions: PendingAction[],
  messages: ChatMessage[],
  options: { context?: string; guildId?: string } = {}
): Promise<ChatAgentResult> {
  const executed: ExecutedAction[] = [];

  for (const action of actions) {
    if (!isToolName(action.tool)) {
      executed.push({
        id: action.id,
        tool: action.tool,
        summary: action.summary,
        ok: false,
        error: "Unknown tool",
      });
      continue;
    }
    const outcome = await executeTool(action.tool, action.args || {});
    executed.push({
      id: action.id,
      tool: action.tool,
      summary: action.summary || summarizeTool(action.tool, action.args || {}),
      ok: outcome.ok,
      result: outcome.result,
      error: outcome.error,
    });
  }

  const report = executed
    .map((e) =>
      e.ok
        ? `OK ${e.tool}: ${e.summary}`
        : `FAIL ${e.tool}: ${e.summary} — ${e.error || "error"}`
    )
    .join("\n");

  const followUp: ChatMessage[] = [
    ...messages.filter((m) => m.role === "user" || m.role === "assistant"),
    {
      role: "user",
      content: `[SYSTEM] The user confirmed these dashboard actions. Results:\n${report}\nAcknowledge what actually happened in character. Do not invent extra successes.`,
    },
  ];

  // Single reply, no tools — just reaction
  const { context = "", guildId = "" } = options;
  const contextBlock = [
    context && `Page context: ${context}`,
    guildId && `Active guild_id: ${guildId}`,
  ]
    .filter(Boolean)
    .join("\n");

  const data = await openRouterChat(
    [
      {
        role: "system",
        content: `${JAMIE_SYSTEM_PROMPT}\n\n--- DASHBOARD CONTEXT ---\n${contextBlock || "None"}`,
      },
      ...followUp,
    ],
    { tools: false, max_tokens: 400, temperature: 0.9 }
  );

  return {
    response: data.choices?.[0]?.message?.content || "It's done.",
    executed,
    pending: [],
  };
}

/** Legacy plain chat (no tools) — kept for simple fallbacks. */
export async function chatWithJamie(
  messages: ChatMessage[],
  context?: string
): Promise<string> {
  const result = await chatWithJamieAgent(messages, { context, maxSteps: 1 });
  // Force one-shot without relying on tools by re-calling without agent if needed
  if (result.response) return result.response;

  const { apiKey, model, apiBase } = getConfig();
  const systemContent = context
    ? `${JAMIE_SYSTEM_PROMPT}\n\n--- DASHBOARD CONTEXT ---\n${context}`
    : JAMIE_SYSTEM_PROMPT;

  const res = await fetch(`${apiBase}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://jamie-dashboard.vercel.app",
      "X-Title": "Jamie Dashboard",
    },
    body: JSON.stringify({
      model,
      messages: [{ role: "system", content: systemContent }, ...messages],
      temperature: 0.9,
      max_tokens: 600,
    }),
    cache: "no-store",
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`LLM API ${res.status}: ${err.slice(0, 200)}`);
  }
  const data = await res.json();
  return data.choices[0].message.content;
}

export async function generateServerBlueprint(description: string): Promise<string> {
  const { apiKey, model, apiBase } = getConfig();

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
