/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: '#007BFF',
      },
      fontFamily: {
        manrope: ['Manrope_700Bold'],
        manropeRegular: ['Manrope_400Regular'],
        inter: ['Inter_400Regular'],
        interBold: ['Inter_700Bold'],
      },
    },
  },
  plugins: [],
}
