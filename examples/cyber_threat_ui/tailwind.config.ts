import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#070B14",
          panel: "#0F172A",
          card: "#111C34",
          accent: "#22D3EE",
          muted: "#93A3B8"
        }
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,238,0.2), 0 0 24px rgba(34,211,238,0.15)"
      }
    }
  },
  plugins: []
} satisfies Config;
