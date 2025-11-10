"use client";

import { useEffect } from 'react';
import { useTheme } from 'next-themes';
import { themes } from '@/lib/themes';
import { getCustomThemes, type CustomTheme } from '@/lib/custom-themes';

/**
 * Hook to apply theme colors to DOM
 *
 * Automatically applies CSS custom properties when theme changes
 * Persists theme selection in localStorage via next-themes
 *
 * Usage: Call this hook in root layout or app component
 */
export function useThemeApplier() {
  const { theme, resolvedTheme } = useTheme();

  useEffect(() => {
    // Skip if not mounted yet
    if (typeof window === 'undefined') return;

    // Get current theme name (use resolvedTheme as fallback)
    const currentThemeName = theme || resolvedTheme;
    if (!currentThemeName) return;

    // For basic light/dark themes, let Tailwind CSS handle it
    if (currentThemeName === 'light' || currentThemeName === 'dark') {
      const root = document.documentElement;
      
      // Remove any custom theme colors to let Tailwind defaults work
      const defaultLightTheme = themes.find(t => t.id === 'default-light');
      const defaultDarkTheme = themes.find(t => t.id === 'default-dark');
      
      const themeColors = currentThemeName === 'dark' ? defaultDarkTheme?.colors : defaultLightTheme?.colors;
      
      if (themeColors) {
        Object.entries(themeColors).forEach(([key, value]) => {
          const cssVar = key.startsWith('--') ? key : `--${key}`;
          root.style.setProperty(cssVar, value as string);
        });
      }

      // Log theme change in development
      if (process.env.NODE_ENV === 'development') {
        console.log(`🎨 Theme applied: ${currentThemeName}`);
      }
      return;
    }

    // For custom themes, find and apply them
    const predefinedTheme = themes.find(t => t.id === currentThemeName || t.name === currentThemeName);

    // If not found in predefined, check custom themes
    let themeColors = predefinedTheme?.colors;

    if (!themeColors) {
      const customThemes = getCustomThemes();
      const customTheme = customThemes.find(t => t.name === currentThemeName);
      themeColors = customTheme?.colors;
    }

    // If still not found, use default-light
    if (!themeColors) {
      const defaultTheme = themes.find(t => t.id === 'default-light');
      themeColors = defaultTheme?.colors;
    }

    // Apply theme colors to DOM
    if (themeColors) {
      const root = document.documentElement;

      Object.entries(themeColors).forEach(([key, value]) => {
        // Add -- prefix if not present
        const cssVar = key.startsWith('--') ? key : `--${key}`;
        root.style.setProperty(cssVar, value as string);
      });

      // Log theme change in development
      if (process.env.NODE_ENV === 'development') {
        console.log(`🎨 Custom theme applied: ${currentThemeName}`);
      }
    }
  }, [theme, resolvedTheme]);
}
