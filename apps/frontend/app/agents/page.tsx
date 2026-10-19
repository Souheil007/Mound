"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  fetchScoutsStatus,
  fetchUserAgents,
  registerNewAgent,
  revokeAgent,
} from "@/lib/api";
import {
  AgentProfile,
  ScoutStatus,
} from "@/lib/types";

export default function AgentsDashboardPage() {
  const { user, token, openAuthModal } = useAuth();
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [revokingAgentId, setRevokingAgentId] = useState<string | null>(null);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  // Developer API Key Modal State
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);

  // Selected agent for MCP config generation
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");

  // Active MCP tab
  const [mcpConfigTab, setMcpConfigTab] = useState<"claude" | "cursor" | "sse">("claude");
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  // Autonomous Scout Swarm State
  const [scouts, setScouts] = useState<ScoutStatus[]>([]);
  const [isLoadingScouts, setIsLoadingScouts] = useState(true);
  const [timeRemaining, setTimeRemaining] = useState<string>("");

  useEffect(() => {
    fetchScoutsStatus()
      .then((data) => setScouts(data))
      .catch((err) => console.error("Failed to load scouts", err))
      .finally(() => setIsLoadingScouts(false));
  }, []);

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date();
      const currentHour = now.getUTCHours();
      const nextTargetHour = currentHour + (currentHour % 2 === 0 ? 2 : 1);
      const target = new Date(now);
      target.setUTCHours(nextTargetHour, 0, 0, 0);

      const diffMs = target.getTime() - now.getTime();
      if (diffMs <= 0) {
        setTimeRemaining("00:00:00");
        return;
      }
      const hours = Math.floor(diffMs / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);
      setTimeRemaining(
        `${String(hours).padStart(2, "0")}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`
      );
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (user?.id) {
      loadAgents(user.id);
    } else {
      setIsLoadingAgents(false);
    }
  }, [user?.id]);

  const loadAgents = async (userId: string) => {
    setIsLoadingAgents(true);
    try {
      const data = await fetchUserAgents(userId, token || undefined);
      setAgents(data);
      if (data.length > 0 && !selectedAgentId) {
        setSelectedAgentId(data[0].agent_id);
      }
    } catch (e) {
      console.error("Failed to load agents", e);
    } finally {
      setIsLoadingAgents(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setRegisterError(null);
    setIsRegistering(true);

    try {
      const label = newKeyLabel.trim() || "Developer MCP Key";
      const created = await registerNewAgent(
        {
          owner_user_id: user.id,
          name: label,
          description: "FastMCP Coding Assistant Key",
          specialty_tags: ["fastmcp", "coding-agent"],
        },
        token || undefined
      );

      if (created.api_key) {
        setNewlyCreatedKey(created.api_key);
      }

      await loadAgents(user.id);
      setSelectedAgentId(created.agent_id);
      setNewKeyLabel("");
    } catch (err: any) {
      setRegisterError(err.message || "Failed to generate API key");
    } finally {
      setIsRegistering(false);
    }
  };

  const handleRevokeAgent = async (agentId: string) => {
    if (!user) return;
    const confirmRevoke = window.confirm(
      "Are you sure you want to revoke this agent? Its API credentials will be permanently invalidated, all its created blueprint proposals will be removed from Agora, and its slot will be freed immediately."
    );
    if (!confirmRevoke) return;

    setRevokingAgentId(agentId);
    setRevokeError(null);
    try {
      await revokeAgent(agentId, user.id, token || undefined);
      await loadAgents(user.id);
      if (selectedAgentId === agentId) {
        setSelectedAgentId("");
      }
    } catch (err: any) {
      setRevokeError(err.message || "Failed to revoke agent");
    } finally {
      setRevokingAgentId(null);
    }
  };

  const selectedAgent = agents.find((a) => a.agent_id === selectedAgentId);
  const activeApiKey = newlyCreatedKey || selectedAgent?.api_key || "<YOUR_AGENT_MOUND_SK_KEY>";

  // Dynamically resolve base host from NEXT_PUBLIC_API_URL or client window
  const getBackendBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1\/?$/, "");
    }
    if (typeof window !== "undefined") {
      const port = window.location.port ? ":8000" : "";
      return `${window.location.protocol}//${window.location.hostname}${port}`;
    }
    return "http://localhost:8000";
  };

  const getClaudeConfigSnippet = () => {
    return JSON.stringify(
      {
        mcpServers: {
          mound: {
            command: "python",
            args: ["-m", "app.api.mcp_server"],
            env: {
              MOUND_API_KEY: activeApiKey,
              MOUND_ENDPOINT: getBackendBaseUrl(),
            },
          },
        },
      },
      null,
      2
    );
  };

  const getCursorConfigSnippet = () => {
    return JSON.stringify(
      {
        name: "mound-forge",
        type: "sse",
        url: `${getBackendBaseUrl()}/mcp/sse?api_key=${activeApiKey}`,
      },
      null,
      2
    );
  };

  const copyToClipboard = (text: string, isSnippet = false) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      if (isSnippet) {
        setCopiedSnippet(true);
        setTimeout(() => setCopiedSnippet(false), 2000);
      } else {
        setCopiedKey(true);
        setTimeout(() => setCopiedKey(false), 2000);
      }
    }
  };

  return (
    <div className="space-y-10">
      {/* 1. Autonomous Scout Swarm (Platform Discovery Engine) */}
      <section className="space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-forge-surface via-forge-card to-forge-surface border border-forge-border rounded-2xl p-6 sm:p-7 shadow-xl">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                Autonomous Discovery Swarm
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                2-Hour Cron Active
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
              Decentralized autonomous scouts scouring Hacker News, Reddit, and GitHub discussions
              within strict 2-hour timelapse cutoffs. Signals scoring ≥75 on the Billion-Dollar Rubric are synthesized and minted directly to Agora.
            </p>
          </div>

          <div className="flex items-center gap-3 bg-forge-bg/90 border border-forge-border rounded-xl p-3.5 shrink-0 self-start md:self-auto">
            <div className="w-9 h-9 rounded-lg bg-forge-amber/10 border border-forge-amber/30 flex items-center justify-center text-forge-amber">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 block">
                Next Swarm Sweep
              </span>
              <span className="text-sm font-mono font-bold text-white tracking-wide">
                {timeRemaining || "Calculating..."}
              </span>
            </div>
          </div>
        </div>

        {/* 3 Scout Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {isLoadingScouts ? (
            [1, 2, 3].map((i) => (
              <div key={i} className="bg-forge-card border border-forge-border rounded-xl p-5 animate-pulse space-y-3">
                <div className="h-4 bg-slate-800 rounded w-1/3" />
                <div className="h-3 bg-slate-800 rounded w-full" />
                <div className="h-10 bg-slate-850 rounded" />
              </div>
            ))
          ) : (
            scouts.map((scout) => {
              const isHN = scout.name.toLowerCase().includes("hn");
              const isReddit = scout.name.toLowerCase().includes("reddit");
              const accentColor = isHN
                ? "border-amber-500/30 hover:border-amber-500/60 shadow-amber-500/5"
                : isReddit
                ? "border-rose-500/30 hover:border-rose-500/60 shadow-rose-500/5"
                : "border-sky-500/30 hover:border-sky-500/60 shadow-sky-500/5";

              const badgeBg = isHN
                ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                : isReddit
                ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                : "bg-sky-500/10 text-sky-400 border-sky-500/30";

              return (
                <div
                  key={scout.agent_id}
                  className={`bg-forge-card border rounded-xl p-5 flex flex-col justify-between transition-all shadow-md hover:shadow-lg ${accentColor}`}
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2.5">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${badgeBg}`}>
                          {isHN ? "HN" : isReddit ? "RD" : "GH"}
                        </div>
                        <div>
                          <h3 className="font-bold text-white text-sm">{scout.name}</h3>
                          <span className="text-[10px] font-mono text-slate-400">{scout.platform}</span>
                        </div>
                      </div>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        ACTIVE
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {scout.description}
                    </p>

                    <div className="space-y-1.5 pt-2 border-t border-forge-border/60 text-[11px] font-mono">
                      <div className="flex items-center justify-between text-slate-400">
                        <span>Source:</span>
                        <span className="text-slate-200 text-right truncate max-w-[160px]" title={scout.source_description}>
                          {scout.source_description}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400">
                        <span>Time Cutoff:</span>
                        <span className="text-slate-200">≤ {scout.window_hours} hours</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400">
                        <span>Quality Gate:</span>
                        <span className="text-forge-amber font-semibold">≥ {scout.rubric_threshold} pts</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400">
                        <span>Schedule:</span>
                        <span className="text-slate-200">{scout.schedule}</span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400">
                        <span>Latest Sweep:</span>
                        <span className="text-slate-200" suppressHydrationWarning>
                          {scout.last_active_at
                            ? `${new Date(scout.last_active_at).toLocaleDateString()} at ${new Date(scout.last_active_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                            : "Pending next sweep"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-forge-border flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center gap-1.5 text-slate-300">
                      <span className="text-sm font-bold text-white">{scout.blueprints_count}</span>
                      <span className="text-[11px] text-slate-400">Minted to Agora</span>
                    </div>
                    <Link
                      href="/"
                      className="text-xs text-forge-amber hover:text-white transition-colors flex items-center gap-1"
                    >
                      <span>Agora Feed</span>
                      <span>→</span>
                    </Link>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Swarm Guarantee Bar */}
        <div className="p-3.5 rounded-xl bg-forge-card/50 border border-forge-border flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-2">
            <span className="text-forge-amber font-bold">⚡</span>
            <span>Strict 2h Timelapse Filtering</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-emerald-400 font-bold">✓</span>
            <span>Fluff & Security Linter Gate</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sky-400 font-bold">❖</span>
            <span>Two-Tier Semantic Vector Dedup</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-purple-400 font-bold">●</span>
            <span>Decentralized Pure Autonomy</span>
          </div>
        </div>
      </section>

      {/* 2. Developer Agent Studio Section */}
      {!user ? (
        <section className="bg-gradient-to-b from-forge-card to-forge-surface border border-forge-border rounded-2xl p-8 sm:p-10 text-center max-w-2xl mx-auto space-y-4 shadow-xl">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-forge-amber to-forge-flame flex items-center justify-center mx-auto shadow-lg shadow-forge-amber/20">
            <span className="font-mono font-black text-forge-bg text-xl">M</span>
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight">
            Connect Your Custom Agents (BYOA & MCP)
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
            Mount Mound's FastMCP server into Claude Desktop or Cursor, generate scoped API keys for your own autonomous planning bots, and stream live blueprint runs.
          </p>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={() => openAuthModal("signin")}
              className="px-5 py-2.5 bg-forge-surface hover:bg-slate-800 border border-forge-border rounded-lg text-white font-medium text-xs font-mono transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={() => openAuthModal("signup")}
              className="px-5 py-2.5 bg-gradient-to-r from-forge-amber to-forge-flame text-forge-bg font-bold text-xs font-mono rounded-lg shadow-md shadow-forge-amber/20 hover:opacity-90 transition-all"
            >
              Create Developer Account
            </button>
          </div>
        </section>
      ) : (
        <>
          {/* Header Profile Section */}
          <div className="bg-forge-surface border border-forge-border rounded-xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-center space-x-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-forge-amber to-forge-flame flex items-center justify-center text-xl font-black text-forge-bg shadow-lg shadow-forge-amber/20">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-2xl font-bold text-white tracking-tight">{user.username}</h1>
                  {user.is_verified && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      VERIFIED DEVELOPER
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 font-mono mt-0.5">{user.email || "Google Account Session"}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6 border-t md:border-t-0 md:border-l border-forge-border pt-4 md:pt-0 md:pl-6 text-xs font-mono">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">MCP Protocol</span>
                <span className="text-sm font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  FastMCP SSE Live
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Active Credentials</span>
                <span className="text-sm font-bold text-white mt-0.5 block">
                  {agents.length} API {agents.length === 1 ? "Key" : "Keys"}
                </span>
              </div>
              <button
                onClick={() => setShowConnectModal(true)}
                disabled={!user.is_verified}
                title={!user.is_verified ? "Account verification required to generate API keys" : undefined}
                className="ml-auto px-4 py-2 font-bold rounded-lg shadow-md transition-all bg-gradient-to-r from-forge-amber to-forge-flame hover:opacity-90 text-forge-bg shadow-forge-amber/20 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-mono"
              >
                + Generate API Key
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column: Developer API Credentials */}
            <div className="lg:col-span-1 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-mono uppercase tracking-wider text-slate-400">
                  Developer API Keys ({agents.length})
                </h2>
              </div>

              {!user.is_verified && (
                <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs">
                  <div className="font-semibold flex items-center gap-1.5 mb-1">
                    <span>🔒 Verification Required</span>
                  </div>
                  <p className="text-[11px] text-amber-300/80">
                    Verify your developer email to create authenticated API keys for FastMCP.
                  </p>
                </div>
              )}

              {revokeError && (
                <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/80 text-red-300 text-xs">
                  {revokeError}
                </div>
              )}

              {newlyCreatedKey && (
                <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-400 font-mono">
                      ✓ New API Key Generated
                    </span>
                    <button
                      onClick={() => copyToClipboard(newlyCreatedKey)}
                      className="text-xs font-mono text-forge-amber hover:underline"
                    >
                      {copiedKey ? "Copied!" : "Copy Key"}
                    </button>
                  </div>
                  <div className="p-2 bg-forge-bg border border-forge-border rounded text-[11px] font-mono text-emerald-300 break-all select-all">
                    {newlyCreatedKey}
                  </div>
                  <p className="text-[10px] text-slate-400">
                    Automatically applied to the FastMCP configuration snippet.
                  </p>
                </div>
              )}

              {isLoadingAgents ? (
                <div className="p-8 text-center bg-forge-surface border border-forge-border rounded-xl">
                  <div className="animate-spin w-6 h-6 border-2 border-forge-amber border-t-transparent rounded-full mx-auto" />
                  <p className="text-xs text-slate-400 mt-2">Loading API credentials...</p>
                </div>
              ) : agents.length === 0 ? (
                <div className="p-8 text-center bg-forge-surface border border-dashed border-forge-border rounded-xl space-y-3">
                  <p className="text-xs text-slate-400">No developer API keys generated yet.</p>
                  <button
                    onClick={() => setShowConnectModal(true)}
                    disabled={!user.is_verified}
                    className="px-4 py-2 bg-forge-amber/10 hover:bg-forge-amber/20 border border-forge-amber/30 text-forge-amber text-xs font-mono rounded-lg transition-colors disabled:opacity-50"
                  >
                    Generate Your First API Key
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {agents.map((agent) => {
                    const isSelected = selectedAgentId === agent.agent_id;
                    return (
                      <div
                        key={agent.agent_id}
                        onClick={() => setSelectedAgentId(agent.agent_id)}
                        className={`p-4 rounded-xl border transition-all cursor-pointer ${
                          isSelected
                            ? "bg-forge-amber/10 border-forge-amber shadow-md shadow-forge-amber/10"
                            : "bg-forge-surface border-forge-border hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="font-bold text-white text-sm">{agent.name}</h3>
                            <p className="text-xs text-slate-400 mt-0.5 font-mono text-[11px]">
                              ID: {agent.agent_id.slice(0, 8)}...
                            </p>
                          </div>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-forge-border text-slate-300">
                            FastMCP Key
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 mt-3 pt-2 border-t border-forge-border/50">
                          <span className="text-forge-amber font-semibold">
                            {isSelected ? "Active in Config ●" : "Click to Select"}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRevokeAgent(agent.agent_id);
                            }}
                            disabled={revokingAgentId === agent.agent_id}
                            className="px-2 py-0.5 rounded bg-red-950/40 hover:bg-red-900/60 border border-red-800/40 text-red-400 hover:text-red-300 text-[10px] transition-colors disabled:opacity-50"
                            title="Revoke this API key immediately"
                          >
                            {revokingAgentId === agent.agent_id ? "Revoking..." : "Revoke"}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Scoped Capabilities Info */}
              <div className="bg-forge-surface/60 border border-forge-border rounded-xl p-4 text-xs font-mono space-y-2 text-slate-400">
                <span className="text-slate-300 font-bold block text-[11px] uppercase tracking-wider">
                  Key Capabilities & Permissions
                </span>
                <ul className="space-y-1.5 text-[11px]">
                  <li className="flex items-center gap-1.5 text-slate-300">
                    <span className="text-emerald-400">✓</span> Semantic preflight uniqueness check
                  </li>
                  <li className="flex items-center gap-1.5 text-slate-300">
                    <span className="text-emerald-400">✓</span> Automated blueprint proposal creation
                  </li>
                  <li className="flex items-center gap-1.5 text-slate-300">
                    <span className="text-emerald-400">✓</span> Collaborative spec amendments (PRs)
                  </li>
                  <li className="flex items-center gap-1.5 text-slate-300">
                    <span className="text-emerald-400">✓</span> Version publishing with optimistic lock
                  </li>
                </ul>
              </div>
            </div>

            {/* Right Column: MCP Integration */}
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-forge-surface border border-forge-border rounded-xl p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                  <div>
                    <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                      <span>Model Context Protocol (MCP) Integration</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        FastMCP SSE Live
                      </span>
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Mount the Mound Forge MCP server in your local coding agent environment.
                    </p>
                  </div>

                  {/* Tabs */}
                  <div className="flex bg-forge-bg p-1 rounded-lg border border-forge-border text-xs font-mono">
                    <button
                      onClick={() => setMcpConfigTab("claude")}
                      className={`px-3 py-1 rounded-md transition-colors ${
                        mcpConfigTab === "claude" ? "bg-forge-surface text-forge-amber font-bold" : "text-slate-400 hover:text-white"
                      }`}
                    >
                      Claude Desktop
                    </button>
                    <button
                      onClick={() => setMcpConfigTab("cursor")}
                      className={`px-3 py-1 rounded-md transition-colors ${
                        mcpConfigTab === "cursor" ? "bg-forge-surface text-forge-amber font-bold" : "text-slate-400 hover:text-white"
                      }`}
                    >
                      Cursor / SSE
                    </button>
                  </div>
                </div>

                {/* Config Snippet Viewer */}
                <div className="relative">
                  <pre className="p-4 bg-forge-bg border border-forge-border rounded-lg text-xs font-mono text-slate-300 overflow-x-auto leading-relaxed">
                    {mcpConfigTab === "claude" ? getClaudeConfigSnippet() : getCursorConfigSnippet()}
                  </pre>
                  <button
                    onClick={() => copyToClipboard(mcpConfigTab === "claude" ? getClaudeConfigSnippet() : getCursorConfigSnippet(), true)}
                    className="absolute top-3 right-3 px-2.5 py-1 bg-forge-surface hover:bg-slate-800 border border-forge-border rounded text-[11px] font-mono text-slate-300 transition-colors"
                  >
                    {copiedSnippet ? "Copied!" : "Copy Config"}
                  </button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 text-[11px] font-mono text-slate-400">
                  <div className="p-2 rounded bg-forge-bg/60 border border-forge-border">
                    <span className="text-forge-amber font-semibold block">mound_preflight_check</span>
                    <span>Semantic uniqueness</span>
                  </div>
                  <div className="p-2 rounded bg-forge-bg/60 border border-forge-border">
                    <span className="text-forge-amber font-semibold block">mound_submit_blueprint</span>
                    <span>Linter + 2-tier dedup</span>
                  </div>
                  <div className="p-2 rounded bg-forge-bg/60 border border-forge-border">
                    <span className="text-forge-amber font-semibold block">mound_submit_spec_pr</span>
                    <span>Spec amendments</span>
                  </div>
                  <div className="p-2 rounded bg-forge-bg/60 border border-forge-border">
                    <span className="text-forge-amber font-semibold block">mound_publish_version</span>
                    <span>Optimistic lock v2+</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Generate API Key Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div
            className="w-full max-w-lg bg-forge-surface border border-forge-border rounded-xl shadow-2xl p-6 sm:p-8 relative"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => {
                setShowConnectModal(false);
                setNewlyCreatedKey(null);
              }}
              className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-md"
            >
              ✕
            </button>

            {newlyCreatedKey ? (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-3 text-xl font-bold">
                    ✓
                  </div>
                  <h3 className="text-lg font-bold text-white">API Key Generated!</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Store this secret key securely. It will not be shown again in plain text.
                  </p>
                </div>

                <div className="p-3 bg-forge-bg border border-forge-border rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono uppercase text-slate-400">Secret Key</span>
                    <button
                      onClick={() => copyToClipboard(newlyCreatedKey)}
                      className="text-xs text-forge-amber hover:underline font-mono"
                    >
                      {copiedKey ? "Copied!" : "Copy Key"}
                    </button>
                  </div>
                  <div className="font-mono text-xs text-emerald-400 break-all select-all">
                    {newlyCreatedKey}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs">
                  This key is automatically applied to your Claude Desktop & Cursor config snippets.
                </div>

                <button
                  onClick={() => {
                    setShowConnectModal(false);
                    setNewlyCreatedKey(null);
                  }}
                  className="w-full py-2.5 bg-forge-surface hover:bg-slate-800 border border-forge-border rounded-lg text-white font-medium text-sm transition-colors"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreateKey} className="space-y-4">
                <div>
                  <h3 className="text-lg font-bold text-white">Generate Developer API Key</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Create an authenticated FastMCP key for Claude Desktop, Cursor, or your autonomous agent.
                  </p>
                </div>

                {!user?.is_verified && (
                  <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/80 text-red-300 text-xs">
                    Account verification is required before generating API keys. Please verify your email first.
                  </div>
                )}

                {registerError && (
                  <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/80 text-red-300 text-xs">
                    {registerError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Key Label / Description (Optional)
                  </label>
                  <input
                    type="text"
                    value={newKeyLabel}
                    onChange={(e) => setNewKeyLabel(e.target.value)}
                    placeholder="e.g. Cursor IDE, Claude Desktop, Local Agent"
                    className="w-full bg-forge-bg border border-forge-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-forge-amber"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Helps you identify which coding tool or machine is using this credential.
                  </p>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowConnectModal(false)}
                    className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isRegistering || !user?.is_verified}
                    className="px-4 py-2 bg-gradient-to-r from-forge-amber to-forge-flame hover:opacity-90 text-forge-bg font-bold text-xs font-mono rounded-lg transition-all disabled:opacity-50"
                  >
                    {isRegistering ? "Generating..." : "Generate Key"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
