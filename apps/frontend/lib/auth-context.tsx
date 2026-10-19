"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  fetchCurrentUser,
  googleAuthUser,
  loginUser,
  registerUser,
  verifyUserCode,
} from "./api";
import { UserProfile } from "./types";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  isAuthModalOpen: boolean;
  authModalTab: "signin" | "signup";
  openAuthModal: (tab?: "signin" | "signup") => void;
  closeAuthModal: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    username: string
  ) => Promise<{ verification_code_hint: string }>;
  verifyCode: (email: string, code: string) => Promise<void>;
  googleLogin: (credential?: string, email?: string, name?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalTab, setAuthModalTab] = useState<"signin" | "signup">("signin");

  useEffect(() => {
    // Rehydrate token from localStorage on client load
    const storedToken = typeof window !== "undefined" ? localStorage.getItem("mound_access_token") : null;
    if (storedToken) {
      setToken(storedToken);
      fetchCurrentUser(storedToken)
        .then((profile) => setUser(profile))
        .catch(() => {
          localStorage.removeItem("mound_access_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const openAuthModal = (tab: "signin" | "signup" = "signin") => {
    setAuthModalTab(tab);
    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
  };

  const login = async (email: string, password: string) => {
    const res = await loginUser({ email, password });
    setToken(res.access_token);
    setUser(res.user);
    if (typeof window !== "undefined") {
      localStorage.setItem("mound_access_token", res.access_token);
    }
    setIsAuthModalOpen(false);
  };

  const register = async (email: string, password: string, username: string) => {
    const res = await registerUser({ email, password, username });
    return { verification_code_hint: res.verification_code_hint };
  };

  const verifyCode = async (email: string, code: string) => {
    const res = await verifyUserCode({ email, code });
    setToken(res.access_token);
    setUser(res.user);
    if (typeof window !== "undefined") {
      localStorage.setItem("mound_access_token", res.access_token);
    }
    setIsAuthModalOpen(false);
  };

  const googleLogin = async (
    credential?: string,
    email?: string,
    name?: string
  ) => {
    const cred = credential || `mock_google_id_token_${Date.now()}`;
    const cleanEmail = email && email.includes("@") ? email.trim() : undefined;
    const cleanName = name?.trim() || (cleanEmail ? cleanEmail.split("@")[0] : undefined);
    const res = await googleAuthUser({
      credential: cred,
      email: cleanEmail,
      name: cleanName,
    });
    setToken(res.access_token);
    setUser(res.user);
    if (typeof window !== "undefined") {
      localStorage.setItem("mound_access_token", res.access_token);
    }
    setIsAuthModalOpen(false);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("mound_access_token");
    }
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const profile = await fetchCurrentUser(token);
      setUser(profile);
    } catch {
      logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthModalOpen,
        authModalTab,
        openAuthModal,
        closeAuthModal,
        login,
        register,
        verifyCode,
        googleLogin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
