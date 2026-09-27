/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}', './app/**/*.{js,jsx,ts,tsx}'],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        // MediScan Brand Colors
        primary: {
          50:  '#EFF6FF',
          100: '#DBEAFE',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          900: '#1E3A8A',
        },
        medical: {
          red:    '#EF4444',
          green:  '#10B981',
          orange: '#F59E0B',
          blue:   '#3B82F6',
          purple: '#8B5CF6',
        },
        dark: {
          bg:      '#0F172A',
          card:    '#1E293B',
          border:  '#334155',
          text:    '#94A3B8',
        }
      },
      fontFamily: {
        sans:  ['Inter-Regular'],
        bold:  ['Inter-Bold'],
        semi:  ['Inter-SemiBold'],
        light: ['Inter-Light'],
      }
    },
  },
  plugins: [],
};
