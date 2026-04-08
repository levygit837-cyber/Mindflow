/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Agent colors
        'agent-teal': '#0D6E6E',
        'agent-indigo': '#5B6ABF', 
        'agent-orange': '#C75D2C',
        'agent-green': '#2D8F5E',
        
        // Surface colors
        'surface-primary': '#0a0a0a',
        'surface-secondary': '#1a1a1a',
        'surface-tertiary': '#2a2a2a',
        'surface-highlight': '#3a3a3a',
        
        // Text colors
        'text-primary': '#ffffff',
        'text-secondary': '#b0b0b0',
        'text-tertiary': '#707070',
        'text-muted': '#505050',
        
        // Border colors
        'border-subtle': '#2a2a2a',
        'border-standard': '#3a3a3a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Fira Code', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-dot': 'pulse-dot 1.4s ease-in-out infinite',
        'pulse-dot-delay-1': 'pulse-dot 1.4s ease-in-out infinite 100ms',
        'pulse-dot-delay-2': 'pulse-dot 1.4s ease-in-out infinite 200ms',
        'blink': 'blink-cursor 1s step-end infinite',
        'search-bounce': 'bounce-search 2s ease-in-out infinite',
        'spin-slow': 'spin-slow 3s linear infinite',
        'stream': 'stream-progress 2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-dot': {
          '0%, 100%': { opacity: '0.2', transform: 'scale(0.8)' },
          '50%': { opacity: '1', transform: 'scale(1)' },
        },
        'blink-cursor': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'bounce-search': {
          '0%': { transform: 'translate(0, 0)' },
          '25%': { transform: 'translate(3px, -3px)' },
          '50%': { transform: 'translate(6px, 0px)' },
          '75%': { transform: 'translate(3px, 3px)' },
          '100%': { transform: 'translate(0, 0)' },
        },
        'spin-slow': {
          'from': { transform: 'rotate(0deg)' },
          'to': { transform: 'rotate(360deg)' },
        },
        'stream-progress': {
          '0%': { width: '0%' },
          '50%': { width: '70%' },
          '100%': { width: '100%' },
        },
      },
      boxShadow: {
        'interactive': '0 0 0 2px var(--agent-teal)',
      },
    },
  },
  plugins: [],
}
