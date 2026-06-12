"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (user.role === "kpmg_admin") router.replace("/admin");
    else router.replace("/chat");
  }, [user, loading, router]);

  return <div className="app-main flex items-center justify-center muted">Loading…</div>;
}
