export default function Loading() {
  return (
    <div className="space-y-8 animate-pulse">
      <div className="space-y-2 border-b border-forge-border pb-6">
        <div className="h-5 w-40 bg-forge-surface rounded" />
        <div className="h-8 w-72 bg-forge-surface rounded" />
        <div className="h-4 w-96 bg-forge-surface rounded" />
      </div>

      <div className="h-10 w-full bg-forge-surface rounded-lg" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-52 bg-forge-card border border-forge-border rounded-xl p-5 space-y-4">
            <div className="flex justify-between items-center">
              <div className="h-4 w-28 bg-forge-surface rounded" />
              <div className="h-6 w-12 bg-forge-surface rounded" />
            </div>
            <div className="h-5 w-3/4 bg-forge-surface rounded" />
            <div className="space-y-2">
              <div className="h-3 w-5/6 bg-forge-surface rounded" />
              <div className="h-3 w-4/6 bg-forge-surface rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
