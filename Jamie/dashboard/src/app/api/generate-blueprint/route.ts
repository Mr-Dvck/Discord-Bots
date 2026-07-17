import { NextResponse } from "next/server";
import { generateServerBlueprint } from "@/lib/llm";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const description: string = body.description || "";
    
    if (!description.trim()) {
      return NextResponse.json({ error: "Description required" }, { status: 400 });
    }

    const raw = await generateServerBlueprint(description);
    
    // Try to parse the JSON from the response
    let blueprint;
    try {
      const start = raw.indexOf("{");
      const end = raw.lastIndexOf("}") + 1;
      if (start >= 0 && end > start) {
        blueprint = JSON.parse(raw.slice(start, end));
      }
    } catch {
      // If parsing fails, return the raw text
    }

    return NextResponse.json({ 
      blueprint: blueprint || null, 
      raw 
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
