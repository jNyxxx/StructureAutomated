import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#050816",
        bg2: "#07111f",
        panel: "#0B1220",
        panel2: "#101A2E",
        panel3: "#111827",
        border: "#243047",
        border2: "#334155",
        text: "#F8FAFC",
        muted: "#93A4BD",
        subtle: "#64748B",
        blue: "#3B82F6",
        blue2: "#2563EB",
        violet: "#8B5CF6",
        cyan: "#22D3EE",
        green: "#22C55E",
        yellow: "#F59E0B",
        red: "#EF4444",
        orange: "#FB923C",
        white: "#FFFFFF",
        black: "#020617",
        locked: "#64748B",
        surface: "#0F172A",
        "surface-light": "#182235",
        goodbg: "#062A1B",
        warnbg: "#2B1F08",
        redbg: "#2B0B13",
        bluebg: "#08213F",
        violetbg: "#1E1238",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        mutedTone: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      fontSize: {
        display: ["52px", { lineHeight: "60px", fontWeight: "800", letterSpacing: "-0.04em" }],
        h1: ["36px", { lineHeight: "44px", fontWeight: "800", letterSpacing: "-0.035em" }],
        h2: ["26px", { lineHeight: "34px", fontWeight: "750", letterSpacing: "-0.025em" }],
        h3: ["20px", { lineHeight: "28px", fontWeight: "700", letterSpacing: "-0.015em" }],
        body: ["15px", { lineHeight: "24px", fontWeight: "500" }],
        table: ["14px", { lineHeight: "22px", fontWeight: "500" }],
        small: ["13px", { lineHeight: "20px", fontWeight: "500" }],
        caption: ["12px", { lineHeight: "18px", fontWeight: "650", letterSpacing: "0.04em" }],
      },
      spacing: {
        "page-desktop": "32px",
        sidebar: "248px",
        topbar: "64px",
        "card-padding": "24px",
        "section-gap": "32px",
        "table-row": "52px",
        "button-height": "44px",
      },
      borderRadius: {
        small: "12px",
        medium: "16px",
        large: "20px",
        xl: "24px",
        pill: "999px",
      },
      boxShadow: {
        panel: "0 18px 60px rgba(2, 6, 23, 0.35)",
        glow: "0 0 0 1px rgba(59, 130, 246, 0.18), 0 24px 80px rgba(2, 6, 23, 0.45)",
      },
    },
  },
  plugins: [animate],
} satisfies Config;

export default config;
