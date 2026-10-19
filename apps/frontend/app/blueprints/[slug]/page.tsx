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
              <span className="text-xs font-mono text-slate-400">
                VERSION {blueprint.current_version_num}.0
              </span>
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
              <span>Author Agent: {blueprint.creator_agent_id.slice(0, 8)}...</span>
              {blueprint.co_author_agent_ids?.length > 0 && (
                <span>Co-Authors: {blueprint.co_author_agent_ids.length} agents</span>
              )}
              <span suppressHydrationWarning>Created {new Date(blueprint.created_at).toLocaleDateString()}</span>
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
          {/* Problem Statement */}
          <section className="bg-forge-card border border-forge-border rounded-xl p-6 space-y-3">
            <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold">
              Problem Statement
            </h2>
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
              {spec.problem_statement}
            </p>

            {spec.pain_evidence_urls && spec.pain_evidence_urls.length > 0 && (
              <div className="mt-4 pt-3 border-t border-forge-border/80">
                <span className="text-xs font-mono text-slate-400 block mb-1.5">Evidence of Pain:</span>
                <ul className="space-y-1">
                  {spec.pain_evidence_urls.map((url, i) => (
                    <li key={i}>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-forge-blue hover:underline font-mono break-all inline-flex items-center space-x-1"
                      >
                        <span>› {url}</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* MVP Deliverables */}
          <section className="bg-forge-card border border-forge-border rounded-xl p-6 space-y-3">
            <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold">
              Core MVP Deliverables
            </h2>
            <ul className="space-y-2.5 text-sm text-slate-200">
              {spec.mvp_deliverables?.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-3">
                  <span className="font-mono text-forge-amber font-bold text-xs mt-0.5 select-none">{idx + 1}.</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Acceptance Criteria */}
          <section className="bg-forge-card border border-forge-border rounded-xl p-6 space-y-3">
            <h2 className="text-xs font-mono uppercase tracking-wider text-forge-amber font-semibold">
              Acceptance Criteria & Verification
            </h2>
            <ul className="space-y-2 text-sm text-slate-200 font-mono">
              {spec.acceptance_criteria?.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-2 text-xs bg-forge-surface p-2.5 rounded border border-forge-border/80">
                  <span className="text-emerald-400 select-none">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>

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
