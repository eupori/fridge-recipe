"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getMe, logout as apiLogout, isLoggedIn, UserResponse } from "./api";

type AuthContextType = {
  user: UserResponse | null;
  loading: boolean;
  checkAuth: () => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const CACHED_USER_KEY = "cached_user";

function getCachedUser(): UserResponse | null {
  try {
    if (typeof window === "undefined") return null;
    const data = localStorage.getItem(CACHED_USER_KEY);
    return data ? JSON.parse(data) : null;
  } catch { return null; }
}

function setCachedUser(user: UserResponse | null) {
  try {
    if (user) localStorage.setItem(CACHED_USER_KEY, JSON.stringify(user));
    else localStorage.removeItem(CACHED_USER_KEY);
  } catch {}
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const cached = getCachedUser();
  const [user, setUser] = useState<UserResponse | null>(cached);
  const [loading, setLoading] = useState(!cached);

  const checkAuth = async () => {
    if (!isLoggedIn()) {
      setUser(null);
      setCachedUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await getMe();
      setUser(userData);
      setCachedUser(userData);
    } catch (err) {
      setUser(null);
      setCachedUser(null);
      // 401(토큰 만료/무효)만 로그아웃, 네트워크 에러 등은 유지
      if (err instanceof Error && err.message === "UNAUTHORIZED") {
        apiLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    apiLogout();
    setUser(null);
    setCachedUser(null);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, checkAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
