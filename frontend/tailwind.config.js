/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef5ff",
          100: "#d9e8ff",
          500: "#2f6df0",
          600: "#1f5ad6",
          700: "#1a49ad",
        },
      },
    },
  },
  plugins: [],
};
