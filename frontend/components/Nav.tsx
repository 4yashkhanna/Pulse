"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/chat", label: "Coach" },
  { href: "/dashboard/employee", label: "My Progress" },
  { href: "/dashboard/manager", label: "Team" },
  { href: "/dashboard/leadership", label: "Leadership" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="nav">
      <Link href="/" className="nav-brand">
        Pulse<em>.</em>
      </Link>
      {LINKS.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`nav-link ${path.startsWith(l.href) ? "active" : ""}`}
        >
          {l.label}
        </Link>
      ))}
      <span className="nav-spacer" />
      <span className="nav-meta">KPMG · DEQ · Prototype</span>
    </nav>
  );
}
