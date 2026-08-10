/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000",
  },
  // When NEXT_PUBLIC_API_BASE is "/api" (e.g. behind a single public tunnel), proxy those
  // calls to the backend server-side. This keeps everything same-origin — one public URL,
  // no CORS, and the backend never has to be exposed directly.
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://localhost:8000/:path*" }];
  },
};

module.exports = nextConfig;
