import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#000000',
        sun: '#FFD500',
        coral: '#FF6B6B',
        sky: '#6BCBFF',
        moss: '#95E06C',
        paper: '#FFF6E9'
      },
      boxShadow: {
        brutal: '8px 8px 0 #000000'
      },
      borderRadius: {
        brutal: '18px'
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'Inter', 'sans-serif']
      }
    }
  },
  plugins: []
};

export default config;
