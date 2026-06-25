/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        xl: "var(--radius)",
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--foreground)",
        },
        popover: {
          DEFAULT: "var(--card)",
          foreground: "var(--foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#e2e8f0",
          foreground: "var(--foreground)",
        },
        muted: {
          DEFAULT: "#e2e8f0",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "#e2e8f0",
          foreground: "var(--foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "#ffffff",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        sidebar: {
          bg: "var(--sidebar-bg)",
          fg: "var(--sidebar-fg)",
          muted: "var(--sidebar-muted)",
          active: "var(--sidebar-active-bg)",
          hover: "var(--sidebar-hover-bg)",
        },
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans SC", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Noto Sans SC", "monospace"],
      },
      boxShadow: {
        neu: "var(--neu-raised)",
        "neu-sm": "var(--neu-raised-sm)",
        "neu-pressed": "var(--neu-pressed)",
        "neu-pressed-sm": "var(--neu-pressed-sm)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
