import { NextResponse } from "next/server";
import {
  chatWithJamieAgent,
  confirmJamieActions,
  type ChatMessage,
} from "@/lib/llm";
import type { PendingAction } from "@/lib/tools";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const messages: ChatMessage[] = body.messages || [];
    const context: string = body.context || "";
    const guildId: string = body.guildId || "";
    const mode: string = body.mode || "chat";

    if (mode === "confirm") {
      const actions: PendingAction[] = body.actions || [];
      if (!actions.length) {
        return NextResponse.json(
          { error: "No actions to confirm" },
          { status: 400 }
        );
      }
      const result = await confirmJamieActions(actions, messages, {
        context,
        guildId,
      });
      return NextResponse.json(result);
    }

    const result = await chatWithJamieAgent(messages, {
      context,
      guildId,
      allowDestructive: false,
    });

    return NextResponse.json(result);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
