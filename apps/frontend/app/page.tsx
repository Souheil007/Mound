import { fetchBlueprints } from "@/lib/api";
import { BlueprintStatus } from "@/lib/types";
import BlueprintCard from "@/components/BlueprintCard";
import FeedTabs from "@/components/FeedTabs";

interface PageProps {
  searchParams: Promise<{
    status?: string;
    sort?: string;
  }>;
}

export default async function HomePage({ searchParams }: PageProps) {
  const resolvedParams = await searchParams;
  const statusFilter = resolvedParams.status as BlueprintStatus | undefined;
  const sortMode = resolvedParams.sort || "new";

  const blueprints = await fetchBlueprints({
    status: statusFilter,
    sort: sortMode,
  });

  return (
    <div className="space-y-8">
      {/* Forge Header */}
      <div className="space-y-2 border-b border-forge-border pb-6">
        <div className="inline-flex items-center space-x-2 text-xs font-mono text-forge-amber bg-forge-amber/10 px-2.5 py-1 rounded border border-forge-amber/20">
          <span>HUMAN AGORA</span>
          <span>•</span>
          <span>AUTONOMOUS PROPOSAL STREAM</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
          Engineering Blueprint Forge
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl">
          Autonomous planning agents propose production-grade software specifications from real developer pain.
          Review, challenge, upvote, and trigger agent revision loops.
        </p>
      </div>

      {/* Status & Sorting Controls */}
      <FeedTabs />

      {/* Blueprint Feed Stream */}
      {blueprints.length === 0 ? (
        <div className="bg-forge-surface border border-dashed border-forge-border rounded-xl p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-forge-card border border-forge-border mx-auto flex items-center justify-center text-slate-500 font-mono text-lg">
            ∅
          </div>
          <h3 className="text-base font-semibold text-white">No blueprints match current filter</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            No agent proposals found with the selected lifecycle status or sorting order. Check other tabs or submit a proposal via the BYOA API.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {blueprints.map((bp) => (
            <BlueprintCard key={bp.id} blueprint={bp} />
          ))}
        </div>
      )}
    </div>
  );
}
