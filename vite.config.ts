import { defineConfig } from "vite";

export default defineConfig({
  build: {
    manifest: true,
    outDir: "src/portfolio/static",
    rollupOptions: {
      input: {
        site: "src/portfolio/static_src/ts/site.ts",
        passkeys: "src/portfolio/static_src/ts/passkeys.ts",
      },
    },
  },
});
