import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        afterglow: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        /** Warm neutral surface system (not proprietary assets) */
        ui: {
          canvas: "#F7F7F4",
          surface: "#FFFFFF",
          muted: "#F1F1EE",
          ink: "#0D0D0D",
          subtle: "#6B6B66",
          line: "#E5E5DF",
          accent: "#111111",
          mint: "#10A37F",
        },
      },
      boxShadow: {
        soft: "0 1px 2px rgba(13, 13, 13, 0.04), 0 1px 3px rgba(13, 13, 13, 0.02)",
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      },
      animation: {
        "pulse-soft": "pulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
