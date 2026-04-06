/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        w: {
          50: '#fff0f3', 100: '#130008', 200: '#2a000f',
          300: '#4a0020', 400: '#7a1030', 500: '#c2185b',
          600: '#e05820', 700: '#ff6040', 800: '#ffb0a0',
        },
        c: {
          50: '#e0f8ff', 100: '#00003a', 200: '#00005a',
          300: '#00007a', 400: '#005080', 500: '#00bcd4',
          600: '#6eb5ff', 700: '#a0d8ff', 800: '#c0f0ff',
        },
        p: {
          50: '#fff0f8', 100: '#fdf6f0', 200: '#f5ebe0',
          300: '#f0d9c8', 400: '#e8cfc0', 500: '#f48fb1',
          600: '#80cbc4', 700: '#4db6ac', 800: '#b2dfdb',
        },
      },
    },
  },
  plugins: [],
}
