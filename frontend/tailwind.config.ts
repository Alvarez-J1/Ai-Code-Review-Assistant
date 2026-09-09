import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        surface: "#f7f8fb",
        ink: "#151922",
        muted: "#687082",
        line: "#d9dee8",
        panel: "#ffffff",
        brand: "#2563eb"
      },
      boxShadow: {
        soft: "0 12px 32px rgba(21, 25, 34, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
