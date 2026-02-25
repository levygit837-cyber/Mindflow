import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    include: [
      "src/**/*.test.{ts,tsx}",
      "frontend/**/*.test.{ts,tsx}",
      "backend/**/*.test.{ts,tsx}",
    ],
    exclude: ["node_modules", "node_modules_old", ".next"],
    environment: "jsdom",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@frontend": path.resolve(__dirname, "./frontend"),
      "@backend": path.resolve(__dirname, "./backend"),
      "@shared": path.resolve(__dirname, "./shared"),
      // Mock server-only for Vitest (it throws in client environments)
      "server-only": path.resolve(__dirname, "./vitest-server-only-mock.ts"),
    },
  },
});
