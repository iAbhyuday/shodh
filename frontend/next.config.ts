import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Silence Turbopack warning in Next.js 16
  turbopack: {},
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*'
      }
    ];
  },
};

export default nextConfig;
