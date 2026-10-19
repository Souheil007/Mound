"use client";

import { useState } from "react";
import { Comment, CritiqueCategory } from "@/lib/types";
import { postCritique, voteComment } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface CritiqueSectionProps {
  blueprintId: string;
  initialComments: Comment[];
  currentUserId?: string;
}

const CATEGORIES: { label: string; value: CritiqueCategory; color: string }[] = [
  { label: "Missing Requirement", value: "MISSING_REQUIREMENT", color: "text-amber-400 bg-amber-500/10 border-amber-500/30" },
  { label: "Architecture Flaw", value: "ARCHITECTURE_FLAW", color: "text-rose-400 bg-rose-500/10 border-rose-500/30" },
  { label: "Simpler Alternative", value: "SIMPLER_ALTERNATIVE", color: "text-sky-400 bg-sky-500/10 border-sky-500/30" },
  { label: "General Feedback", value: "GENERAL_FEEDBACK", color: "text-slate-300 bg-slate-500/10 border-slate-500/30" },
];

export default function CritiqueSection({
  blueprintId,
  initialComments,
  currentUserId,
}: CritiqueSectionProps) {
  const { user, openAuthModal } = useAuth();
  const [comments, setComments] = useState<Comment[]>(initialComments);
  const [category, setCategory] = useState<CritiqueCategory>("MISSING_REQUIREMENT");
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const effectiveUserId = user?.id || currentUserId;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || isSubmitting) return;

    if (!effectiveUserId) {
      openAuthModal("signin");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const created = await postCritique(blueprintId, {
        user_id: effectiveUserId,
        category,
        content: content.trim(),
      });
      setComments([created, ...comments]);
      setContent("");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit critique.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVote = async (commentId: string) => {
    if (!effectiveUserId) {
      openAuthModal("signin");
      return;
    }

    try {
      const res = await voteComment(blueprintId, commentId, effectiveUserId);
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId ? { ...c, upvotes_count: res.upvotes_count } : c
        )
      );
    } catch (err) {
      console.error("Failed to vote comment:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white tracking-tight">Structured Critique Agora</h3>
          <p className="text-xs text-slate-400">
            Submit architectural challenges to trigger agent revisions. 3+ critiques queue an automatic revision loop.
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 bg-forge-surface border border-forge-border rounded text-slate-300">
          {comments.length} Critiques
        </span>
      </div>

      {/* Submission Form */}
      <form onSubmit={handleSubmit} className="bg-forge-card border border-forge-border rounded-xl p-5 space-y-4">
        <div>
          <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
            Critique Category
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                type="button"
                onClick={() => setCategory(c.value)}
                className={`px-3 py-2 rounded-lg text-xs font-medium border text-left transition-all ${
                  category === c.value
                    ? `${c.color} ring-1 ring-forge-amber/40 shadow-sm`
                    : "bg-forge-surface text-slate-400 border-forge-border hover:border-slate-600 hover:text-white"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
            Architectural Critique or Requirement Challenge
          </label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={3}
            placeholder="Identify missing constraints, edge cases, permission limits, or simpler alternatives..."
            className="w-full bg-forge-surface border border-forge-border rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-forge-amber transition-colors"
            required
            minLength={5}
          />
        </div>

        {errorMsg && (
          <p className="text-xs text-rose-400 font-mono">{errorMsg}</p>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting || !content.trim()}
            className="px-4 py-2 rounded-lg bg-forge-amber hover:bg-forge-flame disabled:opacity-50 text-forge-bg font-semibold text-xs tracking-wide transition-colors"
          >
            {isSubmitting ? "Submitting..." : "Submit Critique"}
          </button>
        </div>
      </form>

      {/* Critiques List */}
      <div className="space-y-3">
        {comments.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500 font-mono bg-forge-surface/40 rounded-xl border border-forge-border/60">
            No critiques submitted yet. Be the first developer to challenge this specification.
          </div>
        ) : (
          comments.map((comm) => {
            const cat = CATEGORIES.find((c) => c.value === comm.category) || CATEGORIES[3];
            return (
              <div
                key={comm.id}
                className="bg-forge-card border border-forge-border rounded-xl p-4 space-y-3 transition-colors hover:border-slate-700"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${cat.color}`}>
                      [{cat.label}]
                    </span>
                    {comm.is_addressed ? (
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        ✓ Addressed
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Pending Revision
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => handleVote(comm.id)}
                    className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-forge-surface border border-forge-border hover:border-forge-amber/40 text-xs font-mono text-slate-300 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" strokeWidth="2.5">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
                    </svg>
                    <span>{comm.upvotes_count}</span>
                  </button>
                </div>

                <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">{comm.content}</p>

                <div suppressHydrationWarning className="text-[11px] font-mono text-slate-500">
                  Posted on {new Date(comm.created_at).toLocaleDateString()} at{" "}
                  {new Date(comm.created_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
