"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Nav() {
  const path = usePathname();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  // restore persisted state on mount
  useEffect(() => {
    const saved = localStorage.getItem("pulse_sidebar_collapsed") === "1";
    setCollapsed(saved);
    document.documentElement.classList.toggle("sidebar-collapsed", saved);
  }, []);

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("pulse_sidebar_collapsed", next ? "1" : "0");
    document.documentElement.classList.toggle("sidebar-collapsed", next);
  }

  if (!user || path === "/login") return null;

  const isAdmin = user.role === "kpmg_admin";

  const links = isAdmin
    ? [
        { href: "/admin", label: "Home", icon: "home" },
        { href: "/admin/knowledge", label: "Stage Knowledge", icon: "database" },
      ]
    : [
        { href: "/chat", label: "Chats", icon: "chat" },
        { href: "/knowledge", label: "Team Knowledge", icon: "hub" },
        { href: "/connections", label: "Connections", icon: "power" },
        { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
      ];

  return (
    <nav className="sidebar">
      {/* Collapse / expand toggle */}
      <button
        className="sidebar-toggle"
        onClick={toggle}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
          {collapsed ? "right_panel_open" : "left_panel_close"}
        </span>
      </button>

      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <span className="material-symbols-outlined text-primary icon-fill" style={{ fontSize: 22 }}>
            analytics
          </span>
        </div>
        <div className="nav-label">
          <div className="text-headline-sm font-semibold text-on-primary leading-tight">{isAdmin ? "Pulse Admin" : "Pulse"}</div>
          <div className="text-label-caps text-tertiary-fixed-dim">{isAdmin ? "Intelligence Portal" : "Design Intelligence"}</div>
        </div>
      </div>

      {/* Primary nav */}
      <div className="flex flex-col gap-1 mb-6">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            title={l.label}
            className={`sidebar-nav-item ${
              (l.href === "/admin" ? path === "/admin" || path.startsWith("/admin/org") : path.startsWith(l.href)) ? "active" : ""
            }`}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 22 }}>{l.icon}</span>
            <span className="nav-label">{l.label}</span>
          </Link>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="flex flex-col gap-1 border-t mt-auto pt-4" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <div className="sidebar-nav-item" title={`${user.name} (${user.role})`}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>account_circle</span>
          <div className="flex-1 min-w-0 nav-label">
            <div className="text-body-sm font-medium text-on-primary truncate">{user.name}</div>
            <div className="text-label-caps text-tertiary-fixed-dim capitalize">{user.role}</div>
          </div>
        </div>
        <button
          onClick={logout}
          className="sidebar-nav-item w-full text-left"
          style={{ background: "none", border: "none" }}
          title="Sign out"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>logout</span>
          <span className="nav-label">Sign out</span>
        </button>
      </div>
    </nav>
  );
}
