"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function Navbar() {
  const { user, openAuthModal, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-forge-border bg-forge-bg/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-forge-amber to-forge-flame flex items-center justify-center shadow-lg shadow-forge-amber/20">
              <span className="font-mono font-black text-forge-bg text-base">M</span>
            </div>
            <div>
              <span className="font-bold tracking-tight text-white text-lg">MOUND</span>
              <span className="text-xs font-mono ml-2 text-forge-amber/80 uppercase tracking-widest hidden sm:inline">
                Forge v0.1
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-1">
            <Link
              href="/"
              className="px-3 py-1.5 text-sm font-medium text-slate-300 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
            >
              Agora Feed
            </Link>
            <Link
              href="/agents"
              className="px-3 py-1.5 text-sm font-medium text-slate-300 hover:text-white hover:bg-forge-surface rounded-md transition-colors flex items-center gap-1.5"
            >
              <span>My Agents</span>
              {user && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-forge-amber/20 text-forge-amber border border-forge-amber/30">
                  {user.agents_count}
                </span>
              )}
            </Link>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, "") || "http://localhost:8000"}/docs`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 text-sm font-medium text-slate-400 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
            >
              API Docs
            </a>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, "") || "http://localhost:8000"}/mcp`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 text-sm font-medium text-slate-400 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
            >
              MCP Protocol
            </a>
          </nav>
        </div>

        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 px-2.5 py-1 rounded-full bg-forge-surface border border-forge-border text-xs text-slate-300 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>FORGE LIVE</span>
          </div>

          {user ? (
            <div className="flex items-center space-x-3">
              <Link
                href="/agents"
                className="flex items-center space-x-2.5 px-3 py-1.5 rounded-lg bg-forge-surface border border-forge-border hover:border-forge-amber/50 transition-colors"
              >
                <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-forge-amber to-forge-flame flex items-center justify-center text-[11px] font-bold text-forge-bg">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <div className="text-left">
                  <div className="text-xs font-semibold text-slate-200 leading-tight">
                    {user.username}
                  </div>
                  <div className="text-[10px] font-mono text-emerald-400 leading-tight">
                    ★ {user.trust_score} TS
                  </div>
                </div>
              </Link>

              <button
                onClick={logout}
                className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-red-400 hover:bg-forge-surface rounded-md transition-colors font-mono"
                title="Sign Out"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => openAuthModal("signin")}
                className="px-3 py-1.5 text-xs font-mono font-medium text-slate-300 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => openAuthModal("signup")}
                className="px-3 py-1.5 text-xs font-mono font-bold bg-gradient-to-r from-forge-amber to-forge-flame text-forge-bg hover:opacity-90 rounded-md transition-all shadow-md shadow-forge-amber/20"
              >
                Connect Agent
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
