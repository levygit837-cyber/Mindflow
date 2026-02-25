import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
    resolveAlias: {
      "@frontend": path.resolve(__dirname, "frontend"),
      "@backend": path.resolve(__dirname, "backend"),
      "@shared": path.resolve(__dirname, "shared"),
    },
  },
};

export default nextConfig;
