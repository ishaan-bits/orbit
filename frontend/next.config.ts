import type { NextConfig } from "next";

/**
 * Same-origin API proxy so the browser always talks to `/api/*` on this
 * origin. In production set `API_PROXY_URL` to the deployed FastAPI service
 * (e.g. https://orbit-api.onrender.com); locally it defaults to uvicorn.
 * Set it to an empty string to disable the proxy (direct API mode, which
 * requires `NEXT_PUBLIC_API_URL` and CORS).
 */
const API_PROXY_URL = process.env.API_PROXY_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    if (!API_PROXY_URL) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${API_PROXY_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
