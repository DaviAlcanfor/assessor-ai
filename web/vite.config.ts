import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // 127.0.0.1, não "localhost": no Windows o Node resolve localhost pra ::1 (IPv6)
      // primeiro, mas a API sobe com host="0.0.0.0" (só IPv4) → ECONNREFUSED → o proxy do
      // Vite responde 502. Ver interfaces/api -> main.py:run_api.
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
