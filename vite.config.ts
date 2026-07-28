import { defineConfig } from "vite";

export default defineConfig({
  build: {
    manifest: true,
    outDir: "src/portfolio/static",
    rollupOptions: {
      input: {
        site: "src/portfolio/static_src/ts/site.ts",
        passkeys: "src/portfolio/static_src/ts/passkeys.ts",
        admin: "src/portfolio/static_src/ts/admin.ts",
        editor: "src/portfolio/static_src/ts/editor.ts",
      },
      output: {
        entryFileNames: "assets/[name].js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
});
