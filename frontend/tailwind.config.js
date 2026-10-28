/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hospital: {
          navy: '#0A2540',
          dark: '#0f172a',
          teal: '#0D9488',
          tealLight: '#F0FDFA',
          tealDark: '#0F766E',
          blue: '#0284C7',
          blueLight: '#F0F9FF',
          accent: '#06B6D4',
          gray: '#F8FAFC',
          card: '#FFFFFF',
          border: '#E2E8F0',
          emergency: '#DC2626',
          emergencyLight: '#FEF2F2'
        }
      }
    },
  },
  plugins: [],
}
