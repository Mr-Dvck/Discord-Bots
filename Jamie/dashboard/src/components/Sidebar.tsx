"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/servers", label: "Servers", icon: "🗺️" },
  { href: "/profiles", label: "Profiles", icon: "🧠" },
  { href: "/builder", label: "Server Builder", icon: "🏗️" },
  { href: "/images", label: "Images", icon: "🎨" },
  { href: "/commands", label: "Commands", icon: "⌨️" },
  { href: "/modules", label: "Modules", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className="fixed left-0 top-0 h-screen flex flex-col z-40 transition-all duration-200"
      style={{
        width: collapsed ? 64 : 240,
        background: "var(--surface)",
        borderRight: "1px solid var(--line)",
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-4 py-5 cursor-pointer"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div
          className="flex items-center justify-center rounded-lg text-xl"
          style={{
            width: 36,
            height: 36,
            background: "var(--primary-dim)",
            border: "1px solid var(--primary)",
          }}
        >
          🔥
        </div>
        {!collapsed && (
          <span className="font-bold text-base" style={{ color: "var(--primary)" }}>
            Jamie
          </span>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-medium"
              style={{
                background: active ? "var(--primary-dim)" : "transparent",
                color: active ? "var(--primary)" : "var(--muted)",
                border: active ? "1px solid rgba(57,183,196,0.2)" : "1px solid transparent",
              }}
            >
              <span className="text-lg">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div
        className="px-4 py-3 text-xs cursor-pointer"
        style={{ color: "var(--faint)" }}
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? "→" : "← Collapse"}
      </div>
    </aside>
  );
}
