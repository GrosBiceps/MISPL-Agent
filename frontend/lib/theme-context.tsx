"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Theme = "green" | "purple" | "orange";

const THEME_STORAGE_KEY = "theme";
const THEMES: Theme[] = ["green", "purple", "orange"];

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function isTheme(value: string | null): value is Theme {
  return value !== null && (THEMES as string[]).includes(value);
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("green");

  useEffect(() => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (isTheme(stored)) setThemeState(stored);
    } catch {
      // localStorage indisponible (navigation privée stricte, iframe cross-origin...) — reste sur le thème par défaut.
    }
  }, []);

  function setTheme(next: Theme) {
    setThemeState(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // localStorage indisponible — le thème change quand même pour cette session en mémoire.
    }
    document.documentElement.setAttribute("data-theme", next);
  }

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
