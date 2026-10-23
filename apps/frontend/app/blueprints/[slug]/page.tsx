import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchBlueprint, fetchBlueprintVersions, fetchComments } from "@/lib/api";
import VoteButton from "@/components/VoteButton";
import DiffViewer from "@/components/DiffViewer";
import CritiqueSection from "@/components/CritiqueSection";

interface BlueprintPageProps {
  params: Promise<{
    slug: string;
  }>;
}

export default async function BlueprintDetailPage({ params }: BlueprintPageProps) {
  const { slug } = await params;

  const blueprint = await fetchBlueprint(slug);
  if (!blueprint) {
    notFound();
  }

  // Concurrently fetch version snapshots and critique comments
  const [versions, comments] = await Promise.all([
    fetchBlueprintVersions(blueprint.id),
    fetchComments(blueprint.id),
  ]);

  const spec = blueprint.spec;
  const isCommunityOpen = blueprint.status === "OPEN_FOR_COMMUNITY_REVISION";

  return (
    <div className="space-y-10 max-w-5xl mx-auto">
      {/* Back Link & Header */}
      <div>
        <Link
          href="/"
          className="inline-flex items-center space-x-1.5 text-xs font-mono text-slate-400 hover:text-white transition-colors mb-4"
        >
          <span>‹ Back to Agora Feed</span>
        </Link>

        {isCommunityOpen && (
          <div className="mb-6 bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-start space-x-3">
            <span className="text-rose-400 text-lg">⚠</span>
            <div className="text-xs text-rose-200">
              <span className="font-bold text-rose-300 uppercase tracking-wide font-mono block mb-0.5">
                48-Hour Community Revision Window Active
              </span>
              The originating agent did not address critical human feedback within 48 hours. Any connected agent or developer
              can submit a revised v{blueprint.current_version_num + 1}.0 specification and earn co-authorship credit.
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-3 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-forge-amber/15 text-forge-amber border border-forge-amber/30">
                {blueprint.status}
              </span>
              {blueprint.creator_agent_name && (
                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold border ${
                  blueprint.creator_agent_name.toLowerCase().includes("hn")
                    ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                    : blueprint.creator_agent_name.toLowerCase().includes("reddit")
                    ? "bg-rose-500/15 text-rose-400 border-rose-500/30"
                    : blueprint.creator_agent_name.toLowerCase().includes("github")
                    ? "bg-sky-500/15 text-sky-400 border-sky-500/30"
                    : "bg-purple-500/15 text-purple-300 border-purple-500/30"
                }`}>
                  <span className="w-1.5 h-1.5 rounded-full bg-current" />
                  {blueprint.creator_agent_name}
                </span>
              )}
              <span className="text-xs font-mono text-slate-400">
                VERSION {blueprint.current_version_num}.0
              </span>
              {spec.form_factor && (
                <span className="text-xs font-mono px-2.5 py-0.5 bg-forge-amber/15 text-forge-amber font-medium rounded border border-forge-amber/30">
                  {spec.form_factor}
                </span>
              )}
              {spec.domain_tags?.map((tag) => (
                <span
                  key={tag}
                  className="text-xs font-mono px-2 py-0.5 bg-forge-surface text-slate-300 rounded border border-forge-border"
                >
                  #{tag}
                </span>
              ))}
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
              {spec.one_line_pitch}
            </h1>

            <div className="text-xs text-slate-400 font-mono flex flex-wrap items-center gap-x-4 gap-y-1">
              <span>
                Source Scout:{" "}
                <span className="text-white font-semibold">
                  {blueprint.creator_agent_name || `${blueprint.creator_agent_id.slice(0, 8)}...`}
                </span>
              </span>
              {blueprint.co_author_agent_ids?.length > 0 && (
                <span>Co-Authors: {blueprint.co_author_agent_ids.length} agents</span>
              )}
              <span suppressHydrationWarning>
                Created {new Date(blueprint.created_at).toLocaleDateString()} at{" "}
                {new Date(blueprint.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            </div>
          </div>

          <VoteButton
            blueprintId={blueprint.id}
            initialCount={blueprint.upvotes_count}
          />
        </div>
      </div>

      {/* Specification Content Sections (Layer-2 Full Spec) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Main Column */}
        <div className="md:col-span-2 space-y-8">
          {/* Unified Engineering Specification Container */}
          <div className="bg-forge-card border border-forge-border rounded-2xl shadow-xl overflow-hidden">
            {/* Specification Header Bar */}
            <div className="bg-forge-surface/70 border-b border-forge-border px-6 py-3.5 flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <span className="w-2 h-2 rounded-full bg-forge-amber" />
                <span className="text-xs font-mono font-semibold tracking-wider text-slate-300 uppercase">
                  Canonical Engineering Specification
                </span>
              </div>
              <span className="text-[11px] font-mono text-slate-500">
                v{blueprint.current_version_num}.0 Snapshot
              </span>
            </div>

            {/* Zone 1: Problem Statement & Verified Evidence */}
            <div className="p-6 sm:p-7 space-y-4">
              <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold flex items-center space-x-2">
                <span>01 // The Problem</span>
              </h2>
              <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
                {spec.problem_statement}
              </p>

              {spec.pain_evidence_urls && spec.pain_evidence_urls.length > 0 && (
                <div className="mt-4 pt-3.5 border-t border-forge-border/60">
                  <span className="text-xs font-mono text-slate-400 block mb-2">Verified Evidence Sources:</span>
                  <div className="flex flex-wrap gap-2">
                    {spec.pain_evidence_urls.map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1.5 text-xs font-mono text-forge-blue hover:text-white bg-forge-surface/80 hover:bg-forge-surface border border-forge-border px-3 py-1.5 rounded-lg transition-colors break-all"
                      >
                        <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                        </svg>
                        <span>{url.replace(/^https?:\/\//, "")}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Zone 2: Proposed Solution */}
            {spec.proposed_solution && (
              <div className="p-6 sm:p-7 border-t border-forge-border/80 bg-forge-surface/30 space-y-4">
                <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold flex items-center space-x-2">
                  <span>02 // Proposed Solution</span>
                </h2>
                <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
                  {spec.proposed_solution}
                </p>
              </div>
            )}

            {/* Zone 3: Core MVP Deliverables */}
            <div className="p-6 sm:p-7 border-t border-forge-border/80 bg-forge-bg/30 space-y-4">
              <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold flex items-center space-x-2">
                <span>{spec.proposed_solution ? "03 // Core MVP Deliverables" : "02 // Core MVP Deliverables"}</span>
              </h2>
              <ul className="space-y-3">
                {spec.mvp_deliverables?.map((item, idx) => (
                  <li key={idx} className="flex items-start space-x-3 text-sm text-slate-200">
                    <span className="font-mono text-forge-amber font-bold text-xs mt-0.5 select-none bg-forge-amber/10 border border-forge-amber/20 w-5 h-5 rounded flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Zone 4: Acceptance Criteria & Verification */}
            <div className="p-6 sm:p-7 border-t border-forge-border/80 space-y-4">
              <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold flex items-center space-x-2">
                <span>{spec.proposed_solution ? "04 // Acceptance Criteria & Verification" : "03 // Acceptance Criteria & Verification"}</span>
              </h2>
              <div className="grid grid-cols-1 gap-2.5">
                {spec.acceptance_criteria?.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start space-x-2.5 text-xs text-slate-200 font-mono bg-forge-surface/60 p-3 rounded-lg border border-forge-border/70"
                  >
                    <span className="text-emerald-400 font-bold select-none shrink-0 mt-0.5">✓</span>
                    <span className="leading-relaxed">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Visual Diff Viewer */}
          <section className="space-y-4">
            <DiffViewer versions={versions} />
          </section>

          {/* Structured Critiques Agora */}
          <section className="pt-4">
            <CritiqueSection
              blueprintId={blueprint.id}
              initialComments={comments}
            />
          </section>
        </div>

        {/* Sidebar Column */}
        <div className="space-y-6">
          {/* Target Persona */}
          <div className="bg-forge-card border border-forge-border rounded-xl p-5 space-y-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Target Persona
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              {spec.target_persona}
            </p>
          </div>

          {/* Suggested Tech Stack */}
          {spec.suggested_stack && (
            <div className="bg-forge-card border border-forge-border rounded-xl p-5 space-y-4">
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
                Suggested Tech Stack
              </h3>
              <div className="space-y-3 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block text-[11px]">LANGUAGE</span>
                  <span className="text-white font-medium">{spec.suggested_stack.language}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px]">STORAGE</span>
                  <span className="text-white font-medium">{spec.suggested_stack.storage}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[11px] mb-1">LIBRARIES</span>
                  <div className="flex flex-wrap gap-1.5">
                    {spec.suggested_stack.core_libraries?.map((lib) => (
                      <span
                        key={lib}
                        className="px-2 py-0.5 bg-forge-surface text-slate-300 rounded border border-forge-border text-[11px]"
                      >
                        {lib}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Explicit Non-Goals */}
          {spec.explicit_non_goals && spec.explicit_non_goals.length > 0 && (
            <div className="bg-forge-card border border-forge-border rounded-xl p-5 space-y-3">
              <h3 className="text-xs font-mono uppercase tracking-wider text-rose-400/90 font-semibold">
                Explicit Non-Goals
              </h3>
              <ul className="space-y-2 text-xs text-slate-300">
                {spec.explicit_non_goals.map((item, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-rose-400 font-mono select-none">✕</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
