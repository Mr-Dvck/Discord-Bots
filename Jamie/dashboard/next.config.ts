import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the dashboard to connect to Discord API from server-side
  serverExternalPackages: [],
  // Vercel deployment
  output: "standalone",
};

export default nextConfig;
