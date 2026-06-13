"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

interface SessionState {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (username: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const SessionContext = createContext<SessionState | null>(null);

const TOKEN_KEY = "predictcup.token";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // 啟動時還原 session
  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) {
      setLoading(false);
      return;
    }
    api.auth
      .me(saved)
      .then((u) => {
        setToken(saved);
        setUser(u);
      })
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  const apply = useCallback((t: string, u: User) => {
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setUser(u);
  }, []);

  const login = useCallback(
    async (username: string) => {
      const { token: t, user: u } = await api.auth.devLogin(username);
      apply(t, u);
    },
    [apply]
  );

  const loginWithGoogle = useCallback(
    async (idToken: string) => {
      const { token: t, user: u } = await api.auth.googleLogin(idToken);
      apply(t, u);
    },
    [apply]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    if (!token) return;
    const u = await api.auth.me(token);
    setUser(u);
  }, [token]);

  return (
    <SessionContext.Provider
      value={{ token, user, loading, login, loginWithGoogle, logout, refresh }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
