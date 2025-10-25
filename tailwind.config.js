/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0A0A0F',
          elevated: '#131318',
          subtle: '#171923',
        },
        border: {
          DEFAULT: '#2A2A35',
          hover: '#3A3A45',
        },
        accent: {
          DEFAULT: '#00D3A9',
          hover: '#00BF99',
          subtle: 'rgba(0, 211, 169, 0.1)',
        },
        text: {
          primary: '#FAFAFA',
          secondary: '#A8A8B3',
          tertiary: '#6B6B76',
        },
      },
    },
  },
  plugins: [],
}
