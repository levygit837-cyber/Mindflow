import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    include: [
      "src/**/*.test.{ts,tsx}",
    ],
    exclude: ["node_modules", "node_modules_old", ".next"],
    environment: "jsdom",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@client": path.resolve(__dirname, "./src/client"),
      "@server": path.resolve(__dirname, "./src/server"),
      "@shared": path.resolve(__dirname, "./src/shared"),
      // Mock server-only for Vitest (it throws in client environments)
      "server-only": path.resolve(__dirname, "./vitest-server-only-mock.ts"),
    },
  },
});
