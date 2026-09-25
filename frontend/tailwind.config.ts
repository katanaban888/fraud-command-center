import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#07111f',
        panel: '#0e1b2b',
        line: '#20334b',
      },
    },
  },
  plugins: [],
};

export default config;
