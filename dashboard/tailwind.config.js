/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        scada: {
          bg: "#0B0F19",       // Deep SCADA dark background
          panel: "#161E2E",    // Dark panel background
          border: "#24314A",   // Panel border grey
          nominal: "#10B981",  // Emerald green (normal grid state)
          trip: "#EF4444",     // Red (tripped/fault state)
          warning: "#F59E0B",  // Amber (warning/load stress)
          text: "#E5E7EB",     // Light grey text
          dimText: "#9CA3AF"   // Muted grey text
        }
      },
      fontFamily: {
        mono: ["Consolas", "Fira Code", "Courier New", "monospace"]
      }
    },
  },
  plugins: [],
}
