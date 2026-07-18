import { NextResponse } from "next/server";
import { KNOWLEDGE_BASE, getKnowledgeSection, getSectionsByCategory, getAllCategories } from "@/lib/knowledge-base";

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get("id");
    const category = searchParams.get("category");

    if (id) {
      const section = getKnowledgeSection(id);
      if (!section) {
        return NextResponse.json({ error: "Section not found" }, { status: 404 });
      }
      return NextResponse.json(section);
    }

    if (category) {
      const sections = getSectionsByCategory(category as any);
      return NextResponse.json(sections);
    }

    // Return all sections grouped by category
    const grouped: Record<string, typeof KNOWLEDGE_BASE> = {};
    getAllCategories().forEach(cat => {
      grouped[cat] = getSectionsByCategory(cat);
    });

    return NextResponse.json(grouped);
  } catch (error) {
    console.error("Knowledge base API error:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
