"use client";

import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Mound error caught:", error);
  }, [error]);

  return (
    <div className="bg-forge-surface border border-rose-500/30 rounded-xl p-8 text-center space-y-4 max-w-lg mx-auto my-12">
      <div className="w-10 h-10 rounded-full bg-rose-500/10 text-rose-400 mx-auto flex items-center justify-center font-mono text-base font-bold">
        !
      </div>
      <div>
        <h2 className="text-base font-semibold text-white tracking-tight">System Encountered An Error</h2>
        <p className="text-xs text-slate-400 mt-1 font-mono">{error.message || "Unable to communicate with the Forge backend."}</p>
      </div>
      <div>
        <button
          onClick={() => reset()}
          className="px-4 py-2 bg-forge-card hover:bg-forge-border border border-forge-border rounded-lg text-xs font-mono text-white transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
