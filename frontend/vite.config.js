import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(function (_a) {
    var mode = _a.mode;
    var env = loadEnv(mode, process.cwd(), "");
    var proxyTarget = process.env.VITE_DEV_PROXY_TARGET || env.VITE_DEV_PROXY_TARGET || "http://127.0.0.1:8000";
    return {
        plugins: [react()],
        server: {
            host: "0.0.0.0",
            port: 3000,
            proxy: {
                "/api/v1": {
                    target: proxyTarget,
                    changeOrigin: true,
                },
            },
        },
    };
});
