/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        operational: '#10b981',
        'recently-resolved': '#84cc16',
        degraded: '#f59e0b',
        incident: '#ef4444',
        maintenance: '#3b82f6',
        unknown: '#6b7280',
      },
    },
  },
  plugins: [],
}
