import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  distDir: '.tools/.next',
  turbopack: {
    root: path.resolve(__dirname),
    resolveAlias: {
      "@client": path.resolve(__dirname, "src/client"),
      "@server": path.resolve(__dirname, "src/server"),
      "@shared": path.resolve(__dirname, "src/shared"),
    },
  },
};

export default nextConfig;
