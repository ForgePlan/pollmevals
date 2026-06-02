/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export — the site is a published artifact rendered from a frozen
  // leaderboard.json (no server runtime; deployable to any static host / R2 / Pages).
  output: "export",
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;
