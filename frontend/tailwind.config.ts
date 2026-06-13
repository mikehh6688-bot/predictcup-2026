import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 體育新聞風主色（CTA）
        brand: {
          green: "#059669", // emerald-600
          blue: "#2563eb",  // blue-600
        },
      },
      maxWidth: {
        app: "480px", // Mobile-first 容器寬度
      },
    },
  },
  plugins: [],
};

export default config;
