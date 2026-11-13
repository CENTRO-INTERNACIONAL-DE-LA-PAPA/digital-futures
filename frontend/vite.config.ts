import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development (`npm run dev`) the API runs separately: `uv run digital-futures-web`.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8510" } },
});
