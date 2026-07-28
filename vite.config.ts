import { defineConfig } from "vite";

export default defineConfig({
  build: {
    manifest: true,
    outDir: "src/portfolio/static",
    rollupOptions: {
      input: "src/portfolio/static_src/ts/site.ts",
    },
  },
});
