"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { BlueprintStatus } from "@/lib/types";

const STATUS_FILTERS: { label: string; value: BlueprintStatus | "ALL" }[] = [
  { label: "All Proposals", value: "ALL" },
  { label: "Open", value: "OPEN" },
  { label: "Qualified", value: "QUALIFIED" },
  { label: "Community Revision", value: "OPEN_FOR_COMMUNITY_REVISION" },
  { label: "Ready For Build", value: "READY_FOR_BUILD" },
  { label: "Claimed", value: "CLAIMED" },
];

const SORT_OPTIONS = [
  { label: "Hot", value: "hot" },
  { label: "Top", value: "top" },
  { label: "New", value: "new" },
];

export default function FeedTabs() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const currentStatus = searchParams.get("status") || "ALL";
  const currentSort = searchParams.get("sort") || "new";

  const updateFilters = (status?: string, sort?: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (status !== undefined) {
      if (status === "ALL") params.delete("status");
      else params.set("status", status);
    }
    if (sort !== undefined) {
      params.set("sort", sort);
    }
    router.push(`/?${params.toString()}`);
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-forge-border">
      <div className="flex items-center space-x-1.5 overflow-x-auto pb-2 sm:pb-0 scrollbar-none">
        {STATUS_FILTERS.map((f) => {
          const isActive = currentStatus === f.value;
          return (
            <button
              key={f.value}
              onClick={() => updateFilters(f.value, undefined)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                isActive
                  ? "bg-forge-amber/15 text-forge-amber border border-forge-amber/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-forge-surface border border-transparent"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      <div className="flex items-center space-x-1 bg-forge-surface p-1 rounded-lg border border-forge-border self-start sm:self-auto">
        {SORT_OPTIONS.map((s) => {
          const isActive = currentSort === s.value;
          return (
            <button
              key={s.value}
              onClick={() => updateFilters(undefined, s.value)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                isActive
                  ? "bg-forge-card text-white shadow-sm border border-forge-border"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {s.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
