import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        status: {
          pending: '#f59e0b',
          'in-progress': '#3b82f6',
          starting: '#06b6d4',
          testing: '#8b5cf6',
          completed: '#22c55e',
          failed: '#ef4444',
          rejected: '#f97316',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};

export default config;
