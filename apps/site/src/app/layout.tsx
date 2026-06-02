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
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="shell">
            <Link className="wordmark" href="/">
              <span className="dot" />
              POLLMEVALS
            </Link>
            <nav className="site-nav">
              <Link href="/">Leaderboard</Link>
              <a href="#methodology">Methodology</a>
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
