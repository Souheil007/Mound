"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export default function AuthModal() {
  const {
    isAuthModalOpen,
    authModalTab,
    closeAuthModal,
    openAuthModal,
    login,
    register,
    verifyCode,
    googleLogin,
  } = useAuth();

  const [step, setStep] = useState<"form" | "verify">("form");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [codeHint, setCodeHint] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleTabSwitch = (tab: "signin" | "signup") => {
    setErrorMsg(null);
    setStep("form");
    openAuthModal(tab);
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err: any) {
      if (err.message?.includes("Account is not verified yet")) {
        setStep("verify");
        setErrorMsg("Please enter the verification code sent to your email.");
      } else {
        setErrorMsg(err.message || "Invalid credentials");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);
    try {
      const res = await register(email, password, username);
      setCodeHint(res.verification_code_hint);
      setCode(res.verification_code_hint); // Pre-fill for frictionless local development
      setStep("verify");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to register account");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);
    try {
      await verifyCode(email, code);
    } catch (err: any) {
      setErrorMsg(err.message || "Invalid verification code");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleAuth = async () => {
    setErrorMsg(null);
    setIsSubmitting(true);
    try {
      const validEmail = email && email.includes("@") ? email.trim() : undefined;
      const validName = username ? username.trim() : undefined;
      await googleLogin(undefined, validEmail, validName);
    } catch (err: any) {
      setErrorMsg(err.message || "Google sign-in failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-md bg-forge-surface border border-forge-border rounded-xl shadow-2xl p-6 sm:p-8 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={closeAuthModal}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-md transition-colors"
          aria-label="Close modal"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Forge Header */}
        <div className="text-center mb-6">
          <div className="inline-flex w-12 h-12 rounded-xl bg-gradient-to-br from-forge-amber to-forge-flame items-center justify-center shadow-lg shadow-forge-amber/20 mb-3">
            <span className="font-mono font-black text-forge-bg text-xl">M</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white">
            {step === "verify"
              ? "Verify Your Account"
              : authModalTab === "signin"
              ? "Sign in to Mound Forge"
              : "Create Developer Account"}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {step === "verify"
              ? `We sent a 6-digit confirmation code to ${email}`
              : "Connect your autonomous planning agents via MCP protocol"}
          </p>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 rounded-lg bg-red-950/50 border border-red-800/80 text-red-300 text-xs flex items-start gap-2">
            <span className="font-bold text-red-400">!</span>
            <span>{errorMsg}</span>
          </div>
        )}

        {step === "verify" ? (
          /* Verification Form */
          <form onSubmit={handleVerifyCode} className="space-y-4">
            {codeHint && (
              <div className="p-2.5 rounded-lg bg-forge-amber/10 border border-forge-amber/30 text-forge-amber text-xs flex items-center justify-between">
                <span>Dev Verification Code:</span>
                <span className="font-mono font-bold tracking-widest text-sm bg-forge-amber/20 px-2 py-0.5 rounded">
                  {codeHint}
                </span>
              </div>
            )}

            <div>
              <label className="block text-xs font-mono text-slate-400 mb-1.5 uppercase tracking-wider">
                6-Digit Verification Code
              </label>
              <input
                type="text"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="123456"
                className="w-full text-center text-2xl font-mono tracking-widest bg-forge-bg border border-forge-border rounded-lg px-4 py-3 text-white focus:outline-none focus:border-forge-amber"
                required
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting || code.length !== 6}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-forge-amber to-forge-flame hover:opacity-90 text-forge-bg font-bold text-sm rounded-lg shadow-lg shadow-forge-amber/20 transition-all disabled:opacity-50"
            >
              {isSubmitting ? "Verifying..." : "Verify & Launch Forge"}
            </button>

            <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
              <button
                type="button"
                onClick={() => setStep("form")}
                className="hover:text-white transition-colors"
              >
                ← Back to credentials
              </button>
            </div>
          </form>
        ) : (
          /* Sign In / Sign Up Form */
          <div className="space-y-4">
            {/* Google OAuth Button */}
            <button
              type="button"
              onClick={handleGoogleAuth}
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm font-medium flex items-center justify-center gap-3 transition-colors shadow-sm"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Continue with Google</span>
            </button>

            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-forge-border" />
              <span className="text-[11px] font-mono text-slate-500 uppercase">or with email</span>
              <div className="flex-1 h-px bg-forge-border" />
            </div>

            {/* Tab selector */}
            <div className="flex border-b border-forge-border pb-1">
              <button
                type="button"
                onClick={() => handleTabSwitch("signin")}
                className={`flex-1 py-1.5 text-xs font-mono uppercase tracking-wider text-center transition-colors ${
                  authModalTab === "signin"
                    ? "text-forge-amber border-b-2 border-forge-amber font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => handleTabSwitch("signup")}
                className={`flex-1 py-1.5 text-xs font-mono uppercase tracking-wider text-center transition-colors ${
                  authModalTab === "signup"
                    ? "text-forge-amber border-b-2 border-forge-amber font-bold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Sign Up
              </button>
            </div>

            <form
              onSubmit={authModalTab === "signin" ? handleSignIn : handleSignUp}
              className="space-y-3.5"
            >
              {authModalTab === "signup" && (
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    Username / Handle
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="alex_dev"
                    className="w-full bg-forge-bg border border-forge-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-forge-amber"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="dev@example.com"
                  className="w-full bg-forge-bg border border-forge-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-forge-amber"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  minLength={8}
                  className="w-full bg-forge-bg border border-forge-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-forge-amber"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-forge-amber to-forge-flame hover:opacity-90 text-forge-bg font-bold text-sm rounded-lg shadow-lg shadow-forge-amber/20 transition-all disabled:opacity-50 mt-2"
              >
                {isSubmitting
                  ? "Processing..."
                  : authModalTab === "signin"
                  ? "Sign In"
                  : "Create Account & Verify"}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
