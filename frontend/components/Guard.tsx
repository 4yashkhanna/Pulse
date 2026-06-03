"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Guard({
  role,
  children,
}: {
  role?: "kpmg_admin" | "manager" | "employee" | ("kpmg_admin" | "manager" | "employee")[];
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (role) {
      const allowed = Array.isArray(role) ? role : [role];
      if (!allowed.includes(user.role)) {
        router.replace(user.role === "kpmg_admin" ? "/admin" : "/chat");
      }
    }
  }, [user, loading, role, router]);

  if (loading || !user) return <div className="page muted">Loading…</div>;
  return <>{children}</>;
}
