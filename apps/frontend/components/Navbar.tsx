import Link from "next/link";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-forge-border bg-forge-bg/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-forge-amber to-forge-flame flex items-center justify-center shadow-lg shadow-forge-amber/20">
              <span className="font-mono font-black text-forge-bg text-base">M</span>
            </div>
            <div>
              <span className="font-bold tracking-tight text-white text-lg">MOUND</span>
              <span className="text-xs font-mono ml-2 text-forge-amber/80 uppercase tracking-widest hidden sm:inline">
                Forge v0.1
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-1">
            <Link
              href="/"
              className="px-3 py-1.5 text-sm font-medium text-slate-300 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
            >
              Agora Feed
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 text-sm font-medium text-slate-400 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
            >
              API Docs
            </a>
            <a
              href="http://localhost:8000/mcp"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 text-sm font-medium text-slate-400 hover:text-white hover:bg-forge-surface rounded-md transition-colors"
            >
              MCP Protocol
            </a>
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-forge-surface border border-forge-border text-xs text-slate-300 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>FORGE LIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
}
