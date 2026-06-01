/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  output: process.env.DOCKER_BUILD === "1" ? "standalone" : undefined,
  async rewrites() {
    return [
      {
        source: "/api/ingest",
        destination: `${backendUrl}/api/ingest`,
      },
      {
        source: "/api/session/:path*",
        destination: `${backendUrl}/api/session/:path*`,
      },
      {
        source: "/backend-health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
