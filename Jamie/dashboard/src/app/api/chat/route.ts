import { NextResponse } from "next/server";
import { chatWithJamie, ChatMessage } from "@/lib/llm";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const messages: ChatMessage[] = body.messages || [];
    const context: string = body.context || "";

    const response = await chatWithJamie(messages, context);
    return NextResponse.json({ response });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
