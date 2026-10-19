import Link from "next/link";

export default function NotFound() {
  return (
    <div className="bg-forge-surface border border-forge-border rounded-xl p-10 text-center space-y-4 max-w-lg mx-auto my-12">
      <div className="font-mono text-4xl font-bold text-forge-amber">404</div>
      <div>
        <h2 className="text-lg font-semibold text-white">Blueprint Not Found</h2>
        <p className="text-xs text-slate-400 mt-1">
          The requested specification does not exist in the forge database or was removed.
        </p>
      </div>
      <div>
        <Link
          href="/"
          className="inline-flex items-center px-4 py-2 bg-forge-amber text-forge-bg font-semibold rounded-lg text-xs transition-colors hover:bg-forge-flame"
        >
          Return to Agora Feed
        </Link>
      </div>
    </div>
  );
}
