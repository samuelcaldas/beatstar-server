import type { NextConfig } from "next";

// The export is served by FastAPI under /admin, so every asset and route is prefixed.
const nextConfig: NextConfig = {
  output: "export",
  basePath: "/admin",
  trailingSlash: true,
  reactStrictMode: true,
};

export default nextConfig;
