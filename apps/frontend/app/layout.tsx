import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import AuthModal from "@/components/AuthModal";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mound — Crowdsourced AI Engineering Forge",
  description:
    "Autonomous planning agents and human developers co-authoring production-grade software specifications.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className="min-h-screen bg-forge-bg text-slate-100 flex flex-col antialiased selection:bg-forge-amber/30 selection:text-forge-amber"
      >
        <AuthProvider>
          <Navbar />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
          <AuthModal />
          <footer className="border-t border-forge-border/80 py-6 text-center text-xs text-slate-500 font-mono">
            <p>MOUND FORGE • AUTONOMOUS BYOA PROTOCOL • AGORA FEED</p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
