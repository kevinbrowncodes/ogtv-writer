/**
 * Tailwind CSS configuration.
 *
 * THEME CUSTOMIZATION: the entire app theme is driven by CSS variables defined
 * in `app/static/css/input.css` (see the `:root` and `.dark` blocks). To
 * re-skin an app for a new project, change those variables — you rarely need to
 * touch this file. Dark mode is class-based (`<html class="dark">`).
 *
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  // Scan every place that can contain Tailwind class names.
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Semantic colors mapped to CSS variables (see input.css).
        // Use them like `bg-surface`, `text-muted`, `border-border`, etc.
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        "surface-2": "rgb(var(--color-surface-2) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        content: "rgb(var(--color-content) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        brand: "rgb(var(--color-brand) / <alpha-value>)",
        "brand-fg": "rgb(var(--color-brand-fg) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      borderRadius: {
        xl: "0.875rem",
      },
    },
  },
  plugins: [],
};
