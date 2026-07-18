"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import { KNOWLEDGE_BASE, getAllCategories, getSectionsByCategory } from "@/lib/knowledge-base";

type Category = "personality" | "server" | "commands" | "system" | "behavior";

const categoryLabels: Record<Category, string> = {
  personality: "Personality & Identity",
  server: "Server Knowledge",
  commands: "Commands & Features",
  system: "System Configuration",
  behavior: "Behavior & Learning",
};

const categoryColors: Record<Category, string> = {
  personality: "#a855f7",
  server: "#3b82f6",
  commands: "#22c55e",
  system: "#f97316",
  behavior: "#ec4899",
};

export default function KnowledgeBasePage() {
  const [activeCategory, setActiveCategory] = useState<Category>("personality");
  const [searchTerm, setSearchTerm] = useState("");

  const filteredSections = getSectionsByCategory(activeCategory).filter(
    section =>
      section.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      section.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main
        className="flex-1 ml-[240px] p-8"
        style={{ background: "var(--bg)" }}
      >
        {/* Header */}
        <div className="mb-8">
          <h1
            className="text-3xl font-bold"
            style={{ color: "var(--primary)" }}
          >
            Jamie's Knowledge Base
          </h1>
          <p
            className="text-sm mt-2"
            style={{ color: "var(--muted)" }}
          >
            Compiled personality files, server documentation, and system configuration
          </p>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search knowledge base..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border bg-background"
            style={{
              borderColor: "rgba(57,183,196,0.3)",
              color: "var(--text)",
              background: "var(--bg)",
            }}
          />
        </div>

        {/* Category Tabs */}
        <div
          className="flex flex-wrap gap-2 mb-6"
          style={{ borderBottom: "1px solid rgba(57,183,196,0.2)" }}
        >
          {getAllCategories().map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                activeCategory === cat
                  ? ""
                  : "opacity-60 hover:opacity-100"
              }`}
              style={{
                background: activeCategory === cat ? "var(--bg)" : "transparent",
                color: activeCategory === cat ? "var(--primary)" : "var(--muted)",
                borderColor: activeCategory === cat ? "var(--primary)" : "transparent",
                borderWidth: activeCategory === cat ? "0 0 2px 0" : "0",
                borderStyle: "solid",
              }}
            >
              {categoryLabels[cat]}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="grid gap-4 md:grid-cols-2">
          {filteredSections.map((section) => (
            <div
              key={section.id}
              className="card animate-fade"
              style={{ border: "1px solid rgba(57,183,196,0.2)" }}
            >
              <div
                className="px-6 py-4 border-b"
                style={{ borderColor: "rgba(57,183,196,0.2)" }}
              >
                <div className="flex items-center justify-between">
                  <h3
                    className="text-xl font-bold"
                    style={{ color: "var(--primary)" }}
                  >
                    {section.title}
                  </h3>
                  <span
                    className="px-2 py-1 rounded text-xs font-semibold"
                    style={{
                      background: categoryColors[section.category] + "20",
                      color: categoryColors[section.category],
                    }}
                  >
                    {section.category}
                  </span>
                </div>
              </div>
              <div className="px-6 py-4">
                <div
                  className="prose max-w-none text-sm"
                  style={{ color: "var(--text)" }}
                >
                  {section.content.split("\n").map((line, i) => {
                    if (line.startsWith("## ")) {
                      return (
                        <h4
                          key={i}
                          className="text-lg font-semibold mt-4 mb-2"
                          style={{ color: "var(--primary)" }}
                        >
                          {line.replace("## ", "")}
                        </h4>
                      );
                    }
                    if (line.startsWith("### ")) {
                      return (
                        <h5
                          key={i}
                          className="text-md font-semibold mt-3 mb-2"
                          style={{ color: "var(--primary-dim)" }}
                        >
                          {line.replace("### ", "")}
                        </h5>
                      );
                    }
                    if (line.startsWith("- ")) {
                      return (
                        <p key={i} className="ml-4 mb-1">
                          {line.replace("- ", "")}
                        </p>
                      );
                    }
                    if (line.startsWith("|")) {
                      // Simple table rendering
                      const cells = line.split("|").filter((c) => c.trim());
                      if (cells.length < 2) return null;
                      return (
                        <table key={i} className="w-full text-sm border-collapse mb-2">
                          <tbody>
                            <tr>
                              {cells.map((cell, j) => (
                                <td
                                  key={j}
                                  className="border p-2"
                                  style={{ borderColor: "rgba(57,183,196,0.2)" }}
                                >
                                  {cell.trim()}
                                </td>
                              ))}
                            </tr>
                          </tbody>
                        </table>
                      );
                    }
                    return <p key={i} className="mb-1">{line}</p>;
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty state */}
        {filteredSections.length === 0 && (
          <div
            className="text-center py-12"
            style={{ color: "var(--muted)" }}
          >
            <p className="text-lg">No results found for "{searchTerm}"</p>
          </div>
        )}
      </main>
    </div>
  );
}
