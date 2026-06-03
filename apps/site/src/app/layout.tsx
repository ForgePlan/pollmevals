import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "POLLMEVALS — open evidence for LLM stacks",
  description:
    "An open evidence layer for choosing production LLM stacks. We evaluate complete scaffolding stacks — model × agent CLI × tools × memory × validator — on cost, latency, reliability, and judged agreement.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // suppressHydrationWarning: browser extensions (LanguageTool, Grammarly…)
    // inject attributes like `data-lt-installed` onto <html>/<body> before React
    // hydrates, which trips a false hydration mismatch. This only suppresses the
    // top-level element's own attributes — real content mismatches still warn.
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <header className="site-header">
          <div className="shell">
            <Link className="wordmark" href="/">
              <span className="dot" />
              POLLMEVALS
            </Link>
            <nav className="site-nav">
              <Link href="/">Leaderboard</Link>
              <Link href="/tasks">Tasks</Link>
              <Link href="/#methodology">Methodology</Link>
              <a href="https://github.com/ForgePlan/pollmevals">Source</a>
            </nav>
          </div>
        </header>
        <main className="shell">{children}</main>
        <footer className="site-footer">
          <div className="shell">
            <span>POLLMEVALS — open evidence layer · methodology v0.1.0</span>
            <span>
              Numbers are distributions, never single points. Variance is shown,
              not hidden.
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
