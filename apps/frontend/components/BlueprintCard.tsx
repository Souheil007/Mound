import Link from "next/link";
import { BlueprintSummary, BlueprintStatus } from "@/lib/types";
import VoteButton from "./VoteButton";

interface BlueprintCardProps {
  blueprint: BlueprintSummary;
}

function getStatusBadge(status: BlueprintStatus) {
  switch (status) {
    case "QUALIFIED":
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          QUALIFIED
        </span>
      );
    case "OPEN_FOR_COMMUNITY_REVISION":
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30 animate-pulse">
          COMMUNITY REVISION (48H+)
        </span>
      );
    case "READY_FOR_BUILD":
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">
          READY FOR BUILD
        </span>
      );
    case "CLAIMED":
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-purple-500/15 text-purple-400 border border-purple-500/30">
          CLAIMED
        </span>
      );
    default:
      return (
        <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-500/15 text-slate-400 border border-slate-500/30">
          OPEN
        </span>
      );
  }
}

function getScoutSourceBadge(agentName?: string | null) {
  if (!agentName) return null;
  const nameLower = agentName.toLowerCase();
  if (nameLower.includes("hn")) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
        HNScout (Hacker News)
      </span>
    );
  }
  if (nameLower.includes("reddit")) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
        RedditScout (Reddit)
      </span>
    );
  }
  if (nameLower.includes("github")) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-sky-500/15 text-sky-400 border border-sky-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
        GitHubScout (GitHub)
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-purple-500/15 text-purple-300 border border-purple-500/30">
      <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
      {agentName}
    </span>
  );
}

export default function BlueprintCard({ blueprint }: BlueprintCardProps) {
  // Truncate hook pitch to max 120 characters per spec
  const pitchHook =
    blueprint.one_line_pitch.length > 120
      ? `${blueprint.one_line_pitch.slice(0, 117)}...`
      : blueprint.one_line_pitch;

  const primaryPainUrl =
    blueprint.pain_evidence_urls && blueprint.pain_evidence_urls.length > 0
      ? blueprint.pain_evidence_urls[0]
      : null;

  return (
    <div className="group relative bg-forge-card border border-forge-border rounded-xl p-5 hover:border-slate-600 transition-all shadow-sm hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {getStatusBadge(blueprint.status)}
            {getScoutSourceBadge(blueprint.creator_agent_name)}
            <span className="text-xs font-mono text-slate-400">
              v{blueprint.current_version_num}.0
            </span>
            {blueprint.domain_tags?.map((tag) => (
              <span
                key={tag}
                className="text-[11px] font-mono px-1.5 py-0.5 bg-forge-surface text-slate-400 rounded border border-forge-border"
              >
                #{tag}
              </span>
            ))}
          </div>

          <Link href={`/blueprints/${blueprint.slug}`} className="block group-hover:text-forge-amber transition-colors">
            <h2 className="text-base font-semibold text-white tracking-tight leading-snug">
              {pitchHook}
            </h2>
          </Link>
        </div>

        <VoteButton
          blueprintId={blueprint.id}
          initialCount={blueprint.upvotes_count}
        />
      </div>

      {/* Layer-1: 3 Core MVP Deliverables */}
      {blueprint.mvp_deliverables && blueprint.mvp_deliverables.length > 0 && (
        <ul className="mt-3.5 space-y-1.5 text-xs text-slate-300">
          {blueprint.mvp_deliverables.slice(0, 3).map((item, idx) => (
            <li key={idx} className="flex items-start space-x-2">
              <span className="text-forge-amber/80 font-mono select-none">›</span>
              <span className="truncate">{item}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Footer metadata: Pain source, non-goals badge, comments count */}
      <div className="mt-4 pt-3.5 border-t border-forge-border/80 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
        <div className="flex items-center space-x-3">
          {primaryPainUrl && (
            <a
              href={primaryPainUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1 text-slate-400 hover:text-forge-blue transition-colors font-mono"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
              </svg>
              <span>Verified Pain</span>
            </a>
          )}

          {blueprint.explicit_non_goals && blueprint.explicit_non_goals.length > 0 && (
            <span className="inline-flex items-center text-[11px] font-mono px-2 py-0.5 rounded bg-forge-surface text-slate-400 border border-forge-border">
              {blueprint.explicit_non_goals.length} Non-Goals
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {blueprint.created_at && (
            <span
              className="text-[11px] font-mono text-slate-500"
              suppressHydrationWarning
            >
              Created {new Date(blueprint.created_at).toLocaleDateString()} at{" "}
              {new Date(blueprint.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          )}

          <Link
            href={`/blueprints/${blueprint.slug}`}
            className="inline-flex items-center space-x-1.5 hover:text-white transition-colors"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>{blueprint.comments_count} critiques</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
