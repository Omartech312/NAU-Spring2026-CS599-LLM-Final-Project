export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0F1117',
          secondary: '#1A1D2E',
          card: '#1E2235',
          hover: '#252840',
        },
        accent: {
          primary: '#F0A500',
          secondary: '#00D4AA',
          muted: '#8B6914',
        },
        text: {
          primary: '#F5F5F7',
          secondary: '#A0A0B0',
          muted: '#6B6B7B',
        },
        border: '#2A2D3E',
        success: '#4ECB71',
        error: '#FF6B6B',
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
