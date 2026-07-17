import { NextResponse } from "next/server";
import { buildServer, ServerBlueprint } from "@/lib/discord";

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const blueprint: ServerBlueprint = await req.json();
    const results = await buildServer(id, blueprint);
    return NextResponse.json(results);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
