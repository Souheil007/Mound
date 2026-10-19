"use client";

import { useState } from "react";
import { voteBlueprint } from "@/lib/api";

interface VoteButtonProps {
  blueprintId: string;
  initialCount: number;
  initialVoted?: boolean;
  userId?: string;
}

export default function VoteButton({
  blueprintId,
  initialCount,
  initialVoted = false,
  userId = "00000000-0000-0000-0000-000000000001", // Default demo user UUID
}: VoteButtonProps) {
  const [voted, setVoted] = useState(initialVoted);
  const [count, setCount] = useState(initialCount);
  const [loading, setLoading] = useState(false);

  const handleVote = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (loading) return;

    // Optimistic toggle
    const newVoted = !voted;
    const newCount = newVoted ? count + 1 : Math.max(0, count - 1);
    setVoted(newVoted);
    setCount(newCount);
    setLoading(true);

    try {
      const res = await voteBlueprint(blueprintId, userId);
      setVoted(res.voted);
      setCount(res.upvotes_count);
    } catch (err) {
      // Revert on error
      setVoted(voted);
      setCount(count);
      console.error("Voting failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleVote}
      disabled={loading}
      className={`group flex items-center space-x-1.5 px-3 py-1.5 rounded-md border text-xs font-mono font-semibold transition-all ${
        voted
          ? "bg-forge-amber/20 border-forge-amber/50 text-forge-amber shadow-sm shadow-forge-amber/20"
          : "bg-forge-surface/60 border-forge-border text-slate-400 hover:text-white hover:border-slate-500"
      }`}
      aria-label="Upvote proposal"
    >
      <svg
        className={`w-3.5 h-3.5 transition-transform group-hover:-translate-y-0.5 ${
          voted ? "fill-forge-amber text-forge-amber" : "fill-none stroke-current"
        }`}
        viewBox="0 0 24 24"
        strokeWidth="2.5"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
      </svg>
      <span>{count}</span>
    </button>
  );
}
