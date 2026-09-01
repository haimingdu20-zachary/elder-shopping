import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#26251e",
        cream: "#f7f7f4",
        bone: "#f2f1ed",
        linen: "#e6e5e0",
        stone: "#cdcdc9",
        muted: "#66655f",
        primary: "#34785c",
        forest: "#34785c",
        verdant: "#1f8a65",
        ember: "#f54e00",
        amber: "#c08532",
        warm: "#c08532",
      },
      boxShadow: { soft: "0 14px 32px rgba(38,37,30,.08)" },
    },
  },
  plugins: [],
};

export default config;
