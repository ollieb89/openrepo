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
      fontFamily: {
        display: ['"Recursive"', '"Space Mono"', 'system-ui', 'sans-serif'],
        body: ['"Spectral"', 'Georgia', 'serif'],
      },
      colors: {
        midnight: '#030812',
        aurora: '#6df4ff',
        ember: '#ffb17a',
        emberDeep: '#f36f56',
        bloom: '#ffd7f2',
        steel: '#5e6472',
        mist: '#cdd4e8',
        vault: '#121b2b',
        flare: '#ff9d3b',
        prism: '#8be5ff',
        status: {
          pending: '#e7b85c',
          'in-progress': '#6bb6ff',
          starting: '#00d1ff',
          testing: '#c478ff',
          completed: '#33d686',
          failed: '#ff6777',
          rejected: '#ffb347',
        },
      },
      backgroundImage: {
        cosmic: 'radial-gradient(circle at 10% 20%, rgba(109,244,255,0.4), transparent 40%), radial-gradient(circle at 80% 0%, rgba(255,155,59,0.45), transparent 45%), linear-gradient(135deg, rgba(3, 8, 18, 0.95), rgba(18, 27, 43, 0.95))',
        tide: 'linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0) 100%)',
        aura: 'conic-gradient(from 180deg at 50% 50%, rgba(255,157,59,0.45), rgba(109,244,255,0.25), rgba(255,111,86,0.25), rgba(255,157,59,0.35))',
      },
      boxShadow: {
        halo: '0 25px 45px rgba(3, 8, 18, 0.65), 0 0 35px rgba(141, 229, 255, 0.35)',
        card: '0 10px 30px rgba(3, 8, 18, 0.45)',
      },
      keyframes: {
        drift: {
          '0%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
          '100%': { transform: 'translateY(0px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        drift: 'drift 12s ease-in-out infinite',
        shimmer: 'shimmer 2.5s linear infinite',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};

export default config;
