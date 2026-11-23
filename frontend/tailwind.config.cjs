/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c2b22",
        muted: "#6d786f",
        canvas: "#f6f7f5",
        brand: {
          50: "#eef4ee",
          100: "#dce9dc",
          500: "#5a8065",
          600: "#416b4e",
          700: "#31583e",
        },
      },
      boxShadow: {
        card: "0 10px 35px rgba(28, 43, 34, 0.06)",
      },
    },
  },
  plugins: [],
};
