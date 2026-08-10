"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AuthUser, clearToken, getToken, me } from "./api";

interface AuthCtx {
  user: AuthUser | null;
  loading: boolean;
  logout: () => void;
  setUser: (u: AuthUser | null) => void;
}

const Ctx = createContext<AuthCtx>({
  user: null,
  loading: true,
  logout: () => {},
  setUser: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  function logout() {
    clearToken();
    setUser(null);
    router.push("/login");
  }

  return (
    <Ctx.Provider value={{ user, loading, logout, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
