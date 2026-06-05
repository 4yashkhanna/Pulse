"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Nav() {
  const path = usePathname();
  const { user, logout } = useAuth();

  if (!user || path === "/login") return null;

  const links =
    user.role === "kpmg_admin"
      ? [{ href: "/admin", label: "Organizations" }]
      : [
          { href: "/chat", label: "Coach" },
          { href: "/knowledge", label: "Knowledge" },
          { href: "/dashboard", label: "Performance" },
        ];

  return (
    <nav className="nav">
      <Link href={user.role === "kpmg_admin" ? "/admin" : "/chat"} className="nav-brand">
        Pulse<em>.</em>
      </Link>
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`nav-link ${path.startsWith(l.href) ? "active" : ""}`}
        >
          {l.label}
        </Link>
      ))}
      <span className="nav-spacer" />
      <span className="nav-meta">
        {user.role === "kpmg_admin" ? "KPMG · DEQ" : user.role}
      </span>
      <span className="nav-meta" style={{ opacity: 0.8 }}>
        {user.name}
      </span>
      <button
        onClick={logout}
        className="nav-link"
        style={{ background: "none", border: "none", cursor: "pointer" }}
      >
        Sign out
      </button>
    </nav>
  );
}
