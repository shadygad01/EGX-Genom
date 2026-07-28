import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// GitHub Pages serves this as a project site at
// https://shadygad01.github.io/EGX-Genom/, so production asset URLs must be
// rooted under /EGX-Genom/. The dev server keeps serving at "/" so local
// `npm run dev -w web` (and its /api proxy) is unaffected.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/EGX-Genom/" : "/",
  plugins: [react()],
  // This package is an npm workspace symlink. Force every dependency to use
  // the workspace's single React runtime or hooks can bind to a second copy
  // and crash the application in the browser.
  resolve: {
    dedupe: ["react", "react-dom"],
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:3001",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
}));
