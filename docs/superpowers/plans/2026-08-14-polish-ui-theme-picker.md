# Polish UI, icône assistant et sélecteur de thème — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une icône robot pour l'assistant, un sélecteur de thème de couleur (vert/violet/orange) accessible depuis un nouveau menu compte, et polir la landing page + l'UI du chat.

**Architecture:** Un attribut `data-theme` sur `<html>` piloté par un `ThemeContext` React + `localStorage`, avec un script anti-flash chargé via `next/script` (`strategy="beforeInteractive"`). Tous les composants qui utilisaient des couleurs vertes codées en dur basculent sur des tokens CSS thématiques déjà définis dans `globals.css`. Deux nouveaux composants d'avatar (icône robot, badge initiales) remplacent les data-URI SVG existants pour permettre la réactivité au thème (une image `data-URI` ne peut pas lire les variables CSS de la page hôte).

**Tech Stack:** Next.js 16 (App Router, TypeScript), CSS pur (pas de Tailwind), `next/script`.

**Spec:** `docs/superpowers/specs/2026-08-14-polish-ui-theme-picker-design.md`

## Global Constraints

- Aucun framework de test frontend n'est configuré dans ce projet (pas de Jest/Vitest, pas de script `"test"`). Vérification via `npx tsc --noEmit` et `npm run build` (depuis `frontend/`), plus vérification manuelle en navigateur décrite dans chaque tâche.
- Trois thèmes exacts : `green` (défaut), `purple`, `orange`. Couleurs de base : vert `#6f7d6a`/`#5a6656`, violet `#5F4D84`, orange `#D66E0B` (valeurs exactes fournies par l'utilisateur).
- Préférence de thème persistée en `localStorage` uniquement (clé `"theme"`), pas de changement backend/compte.
- **Raffinement d'implémentation par rapport au spec approuvé** : en plus des tokens `--accent` / `--accent-solid` / `--accent-solid-text` / `--accent-soft` déjà validés, ce plan introduit un cinquième token **`--accent-text`** — la couleur à utiliser quand `--accent` sert de **texte** sur un fond clair (boutons ghost, badge Beta, code inline), distinct de `--accent-solid-text` qui sert quand le texte est sur un fond **plein** de la couleur du thème. Nécessaire car pour l'orange, une même couleur ne peut pas être à la fois un fond clair-compatible (texte foncé dessus) ET un texte foncé-compatible (sur fond clair) — voir le calcul de contraste dans la Task 1. Ratios vérifiés (formule de luminance relative WCAG) :
  - `--accent-text` vert `#5a6656` sur fond `#faf9f6` : ~6,0:1 ✅
  - `--accent-text` violet `#5F4D84` sur fond `#faf9f6` : ~7,2:1 ✅
  - `--accent-text` orange `#A85A0C` (teinte assombrie, PAS `#D66E0B` brut) sur fond `#faf9f6` : ~5,08:1 ✅ (`#D66E0B` brut donnerait ~3,44:1, sous le seuil AA)
- Les badges de certitude (`.cert-certain`/`.cert-probable`/`.cert-check`) restent **invariants au thème** — ce sont des couleurs sémantiques (succès/prudence/danger), pas des couleurs de marque. `.cert-certain` doit donc être codé en dur (pas de `var(--accent)`) pour ne pas se découpler visuellement si le texte reste vert alors que la bordure suivrait un autre thème.
- Une image chargée via `<img src="data:image/svg+xml,...">` est un document séparé : les `var(--accent)` qu'elle contiendrait ne résolvent PAS les variables CSS de la page hôte. Les avatars doivent donc être des éléments DOM/SVG inline (pas des data-URI) pour réagir au changement de thème.

---

## File Structure

**Nouveaux fichiers :**
- `frontend/lib/theme-context.tsx` — `ThemeProvider`, hook `useTheme()`, type `Theme`.
- `frontend/components/AssistantAvatarIcon.tsx` — icône robot inline (remplace `ASSISTANT_AVATAR`).
- `frontend/components/UserAvatarBadge.tsx` — badge initiales utilisateur (remplace `svgAvatar(...)`).
- `frontend/components/AccountMenu.tsx` — menu déroulant compte + sélecteur de thème.

**Fichiers modifiés :**
- `frontend/app/globals.css` — tokens de thème, règles `button`/`.ghost`/`.card code`/`.cert-certain`, focus des champs, `.example-card`.
- `frontend/app/layout.tsx` — script anti-flash + `ThemeProvider`.
- `frontend/components/BetaBadge.tsx` — couleur de texte migrée vers `--accent-text`.
- `frontend/components/ChatMessage.tsx` — icônes + couleurs (Task 2), espacement/ombre (Task 5).
- `frontend/components/ThinkingIndicator.tsx` — icône robot.
- `frontend/lib/avatar.ts` — suppression de `svgAvatar`/`ASSISTANT_AVATAR` (remplacés), conservation de `getInitials`.
- `frontend/app/chat/page.tsx` — intégration du menu compte dans le header.
- `frontend/app/page.tsx` — bandeau de réassurance, halo, bouton thématisé.
- `frontend/components/EmptyState.tsx` — classe `.example-card` au lieu de `.ghost`.

---

### Task 1: Système de thème — tokens CSS, contexte React, script anti-flash

**Files:**
- Modify: `frontend/app/globals.css:1-70` (tokens + règles `button`/`.ghost`)
- Modify: `frontend/app/globals.css:103-125` (`.card code`)
- Modify: `frontend/app/globals.css:181-205` (`.cert-certain`)
- Modify: `frontend/components/BetaBadge.tsx`
- Create: `frontend/lib/theme-context.tsx`
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Produces : `Theme = "green" | "purple" | "orange"`, `ThemeProvider({children})`, `useTheme() -> { theme: Theme; setTheme: (t: Theme) => void }`, exportés depuis `frontend/lib/theme-context.tsx` — consommés par Task 3 (`AccountMenu`).
- Produces : tokens CSS `--accent`, `--accent-solid`, `--accent-solid-text`, `--accent-soft`, `--accent-text` — consommés par toutes les tâches suivantes.

- [ ] **Step 1: Remplacer le bloc de tokens et les règles `button`/`.ghost` dans `globals.css`**

Remplacer les lignes 1-14 (`:root { ... }`) par :

```css
:root {
  --bg: #faf9f6;
  --surface: #ffffff;
  --ink: #1a1a1a;
  --ink-soft: #5c5c5c;
  --line: #e6e3dc;
  --accent: #6f7d6a;
  --accent-text: #5a6656;
  --accent-solid: #5a6656;
  --accent-solid-text: #ffffff;
  --accent-soft: #eef0ec;
  --danger: #a8584f;
  --radius: 14px;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.03), 0 8px 24px rgba(0, 0, 0, 0.04);
  --serif: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  --sans: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
}

:root[data-theme="green"] {
  --accent: #6f7d6a;
  --accent-text: #5a6656;
  --accent-solid: #5a6656;
  --accent-solid-text: #ffffff;
  --accent-soft: #eef0ec;
}

:root[data-theme="purple"] {
  --accent: #5F4D84;
  --accent-text: #5F4D84;
  --accent-solid: #5F4D84;
  --accent-solid-text: #ffffff;
  --accent-soft: #eeebf4;
}

:root[data-theme="orange"] {
  --accent: #D66E0B;
  --accent-text: #A85A0C;
  --accent-solid: #D66E0B;
  --accent-solid-text: #1a1a1a;
  --accent-soft: #faecdc;
}
```

Puis remplacer les règles `button`/`button.ghost` (actuellement lignes 49-70) par :

```css
button {
  font-family: inherit;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid var(--accent-solid);
  background: var(--accent-solid);
  color: var(--accent-solid-text);
  padding: 10px 18px;
  border-radius: 10px;
  transition: opacity 0.15s;
}
button:hover {
  opacity: 0.88;
}
button:disabled {
  opacity: 0.5;
  cursor: default;
}
button.ghost {
  background: transparent;
  color: var(--accent-text);
  border-color: var(--accent-text);
}
```

- [ ] **Step 2: Migrer `.card code` vers `--accent-text`**

Dans `globals.css`, remplacer :

```css
.card code {
  font-family: "Cascadia Code", "Consolas", "SFMono-Regular", monospace;
  background: var(--accent-soft);
  color: var(--accent);
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 0.85em;
}
```

par (seule la ligne `color` change) :

```css
.card code {
  font-family: "Cascadia Code", "Consolas", "SFMono-Regular", monospace;
  background: var(--accent-soft);
  color: var(--accent-text);
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 0.85em;
}
```

- [ ] **Step 3: Rendre `.cert-certain` invariant au thème**

Remplacer :

```css
.cert-certain {
  background: var(--accent-soft);
  color: #5a6656;
  border: 1px solid var(--accent);
}
```

par (valeurs codées en dur, plus aucune référence à `var(--accent...)`) :

```css
.cert-certain {
  background: #eef0ec;
  color: #5a6656;
  border: 1px solid #6f7d6a;
}
```

- [ ] **Step 4: Migrer `BetaBadge.tsx` vers `--accent-text`**

Dans `frontend/components/BetaBadge.tsx`, changer la ligne :

```tsx
        color: "var(--accent)",
```

en :

```tsx
        color: "var(--accent-text)",
```

- [ ] **Step 5: Créer `frontend/lib/theme-context.tsx`**

```tsx
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
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (isTheme(stored)) setThemeState(stored);
  }, []);

  function setTheme(next: Theme) {
    setThemeState(next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
  }

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
```

- [ ] **Step 6: Ajouter le script anti-flash et `ThemeProvider` dans `layout.tsx`**

Remplacer tout le contenu de `frontend/app/layout.tsx` par :

```tsx
import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { ThemeProvider } from "../lib/theme-context";

export const metadata: Metadata = {
  title: "MISPL Agent",
  description: "Assistant IA pour le paramétrage GLIMS/MISPL",
};

const THEME_INIT_SCRIPT = `
(function () {
  try {
    var t = localStorage.getItem('theme');
    if (t === 'purple' || t === 'orange') {
      document.documentElement.setAttribute('data-theme', t);
    }
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_INIT_SCRIPT}
        </Script>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 7: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 8: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 9: Commit**

```bash
git add frontend/app/globals.css frontend/app/layout.tsx frontend/components/BetaBadge.tsx frontend/lib/theme-context.tsx
git commit -m "feat(frontend): système de thème (vert/violet/orange) avec tokens CSS et anti-flash"
```

---

### Task 2: Icône robot assistant et migration des couleurs d'avatar/bulle

**Files:**
- Create: `frontend/components/AssistantAvatarIcon.tsx`
- Create: `frontend/components/UserAvatarBadge.tsx`
- Modify: `frontend/components/ChatMessage.tsx`
- Modify: `frontend/components/ThinkingIndicator.tsx`
- Modify: `frontend/lib/avatar.ts`

**Interfaces:**
- Consumes : tokens `--accent-soft`, `--accent-solid`, `--accent-solid-text` (Task 1).
- Produces : `AssistantAvatarIcon({ size?: number })` (défaut `size=32`), `UserAvatarBadge({ initials: string, size?: number })` (défaut `size=32`), exportés par défaut — consommés par Task 5 (retouches d'espacement sur `ChatMessage.tsx`, sans changer ces deux composants).

- [ ] **Step 1: Créer `frontend/components/AssistantAvatarIcon.tsx`**

```tsx
interface Props {
  size?: number;
}

export default function AssistantAvatarIcon({ size = 32 }: Props) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0f172a",
        color: "var(--accent-soft)",
      }}
    >
      <svg
        width={size * 0.6}
        height={size * 0.6}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect x="5" y="8" width="14" height="11" rx="3" stroke="currentColor" strokeWidth="1.6" />
        <line x1="12" y1="8" x2="12" y2="4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <circle cx="12" cy="3" r="1.3" fill="currentColor" />
        <circle cx="9.5" cy="13" r="1.3" fill="currentColor" />
        <circle cx="14.5" cy="13" r="1.3" fill="currentColor" />
        <line x1="9" y1="17" x2="15" y2="17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <line x1="2" y1="12" x2="5" y2="12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        <line x1="19" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </div>
  );
}
```

- [ ] **Step 2: Créer `frontend/components/UserAvatarBadge.tsx`**

```tsx
interface Props {
  initials: string;
  size?: number;
}

export default function UserAvatarBadge({ initials, size = 32 }: Props) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--accent-solid)",
        color: "var(--accent-solid-text)",
        fontFamily: "var(--sans)",
        fontSize: 13,
        fontWeight: 600,
      }}
    >
      {initials}
    </div>
  );
}
```

- [ ] **Step 3: Réécrire `frontend/lib/avatar.ts`**

Remplacer tout le contenu du fichier par :

```ts
export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
```

- [ ] **Step 4: Réécrire `frontend/components/ChatMessage.tsx`**

Remplacer tout le contenu du fichier par :

```tsx
import ReactMarkdown from "react-markdown";
import { SourceOut } from "../lib/api";
import { extractCertainty } from "../lib/certainty";
import CodeBlock from "./CodeBlock";
import AssistantAvatarIcon from "./AssistantAvatarIcon";
import UserAvatarBadge from "./UserAvatarBadge";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
  userInitials?: string;
}

const CERTAINTY_LABEL: Record<string, string> = {
  certain: "✅ Certain",
  probable: "⚠️ Probable",
  check: "🔬 À vérifier",
};

const CERTAINTY_CLASS: Record<string, string> = {
  certain: "cert-certain",
  probable: "cert-probable",
  check: "cert-check",
};

export default function ChatMessage({ role, content, sources, warning, userInitials }: Props) {
  if (role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "flex-start", gap: 8, margin: "12px 0" }}>
        <span
          style={{
            display: "inline-block",
            background: "var(--accent-solid)",
            color: "var(--accent-solid-text)",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "80%",
            fontSize: 14,
          }}
        >
          {content}
        </span>
        <UserAvatarBadge initials={userInitials || "?"} />
      </div>
    );
  }

  const { level, rationale, cleanedContent } = extractCertainty(content);

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "12px 0" }}>
      <AssistantAvatarIcon />
      <div style={{ flex: 1, minWidth: 0 }}>
        {warning && warning.length > 0 && (
          <div className="warning-banner">
            ⚠️ Donnée potentiellement sensible détectée ({warning.join(", ")})
          </div>
        )}
        <div className="card" style={{ fontSize: 14, lineHeight: 1.6 }}>
          {level && (
            <div style={{ marginBottom: 10 }}>
              <span className={`cert-badge ${CERTAINTY_CLASS[level]}`}>{CERTAINTY_LABEL[level]}</span>
              {rationale && <span style={{ marginLeft: 8, fontSize: 12.5, color: "var(--ink-soft)" }}>{rationale}</span>}
            </div>
          )}
          <ReactMarkdown components={{ pre: CodeBlock }}>{cleanedContent}</ReactMarkdown>
        </div>
        {sources && sources.length > 0 && (
          <details style={{ marginTop: 6, fontSize: 12.5 }}>
            <summary style={{ cursor: "pointer", color: "var(--ink-soft)" }}>
              Sources documentaires ({sources.length})
            </summary>
            <ul style={{ marginTop: 8, paddingLeft: 18 }}>
              {sources.map((s, i) => (
                <li key={i} style={{ marginBottom: 4 }}>
                  <strong>{s.exact_match ? "EXACT" : `#${i + 1}`}</strong>
                  {s.function_name && ` · ${s.function_name}`}
                  <br />
                  <span style={{ color: "var(--ink-soft)" }}>{s.source}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Réécrire `frontend/components/ThinkingIndicator.tsx`**

Remplacer tout le contenu du fichier par :

```tsx
import AssistantAvatarIcon from "./AssistantAvatarIcon";

export default function ThinkingIndicator() {
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "12px 0" }}>
      <AssistantAvatarIcon />
      <div className="thinking">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <span style={{ marginLeft: 6 }}>Recherche dans la documentation GLIMS...</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur (confirme au passage qu'aucun autre fichier n'importe encore `svgAvatar`/`ASSISTANT_AVATAR` depuis `avatar.ts`)

- [ ] **Step 7: Commit**

```bash
git add frontend/components/AssistantAvatarIcon.tsx frontend/components/UserAvatarBadge.tsx frontend/lib/avatar.ts frontend/components/ChatMessage.tsx frontend/components/ThinkingIndicator.tsx
git commit -m "feat(frontend): icône robot assistant, avatars et bulles réactifs au thème"
```

---

### Task 3: Menu compte avec sélecteur de thème

**Files:**
- Create: `frontend/components/AccountMenu.tsx`
- Modify: `frontend/app/chat/page.tsx:207-220`

**Interfaces:**
- Consumes : `useTheme()`, `Theme` (Task 1) ; `UserAvatarBadge`, `getInitials` (Task 2).
- Produces : `AccountMenu({ displayName: string, onLogout: () => void })`, export par défaut — consommé par `frontend/app/chat/page.tsx`.

- [ ] **Step 1: Créer `frontend/components/AccountMenu.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme, Theme } from "../lib/theme-context";
import { getInitials } from "../lib/avatar";
import UserAvatarBadge from "./UserAvatarBadge";

const THEME_OPTIONS: { value: Theme; label: string; swatch: string }[] = [
  { value: "green", label: "Vert", swatch: "#6f7d6a" },
  { value: "purple", label: "Violet", swatch: "#5F4D84" },
  { value: "orange", label: "Orange", swatch: "#D66E0B" },
];

interface Props {
  displayName: string;
  onLogout: () => void;
}

export default function AccountMenu({ displayName, onLogout }: Props) {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={menuRef} style={{ position: "relative" }}>
      <button
        className="ghost"
        onClick={() => setOpen((v) => !v)}
        style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px" }}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <UserAvatarBadge initials={getInitials(displayName)} size={26} />
        <span style={{ fontSize: 13.5 }}>{displayName}</span>
      </button>
      {open && (
        <div
          className="card"
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: 220,
            padding: 16,
            zIndex: 10,
          }}
        >
          <p
            style={{
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--ink-soft)",
              marginBottom: 10,
            }}
          >
            Couleur de l&apos;interface
          </p>
          <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTheme(opt.value)}
                aria-label={opt.label}
                aria-pressed={theme === opt.value}
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: opt.swatch,
                  border: theme === opt.value ? "2px solid var(--ink)" : "2px solid transparent",
                  padding: 0,
                  cursor: "pointer",
                }}
              />
            ))}
          </div>
          <button className="ghost" onClick={onLogout} style={{ width: "100%", textAlign: "left", padding: "8px 0" }}>
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Intégrer `AccountMenu` dans le header de `frontend/app/chat/page.tsx`**

Ajouter l'import (après l'import de `ConversationSidebar`) :

```tsx
import AccountMenu from "../../components/AccountMenu";
```

Remplacer le bloc `<header>` actuel :

```tsx
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
              <BetaBadge />
            </div>
            <p style={{ color: "var(--ink-soft)", fontSize: 13 }}>{user.display_name}</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="ghost" onClick={handleLogout}>
              Déconnexion
            </button>
          </div>
        </header>
```

par :

```tsx
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
            <BetaBadge />
          </div>
          <AccountMenu displayName={user.display_name} onLogout={handleLogout} />
        </header>
```

- [ ] **Step 3: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 4: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 5: Commit**

```bash
git add frontend/components/AccountMenu.tsx frontend/app/chat/page.tsx
git commit -m "feat(frontend): menu compte avec sélecteur de thème"
```

---

### Task 4: Landing page — bandeau de réassurance, halo, bouton thématisé

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes : tokens `--accent-solid`, `--accent-solid-text`, `--accent-soft` (Task 1).

- [ ] **Step 1: Réécrire `frontend/app/page.tsx`**

Remplacer tout le contenu du fichier par :

```tsx
import Link from "next/link";
import BetaBadge from "../components/BetaBadge";

export default function Home() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "0 20px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          width: 640,
          height: 640,
          transform: "translate(-50%, -50%)",
          background: "radial-gradient(circle, var(--accent-soft) 0%, transparent 70%)",
          opacity: 0.6,
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 24,
          left: 24,
          fontFamily: "var(--serif)",
          fontWeight: 600,
          fontSize: 15,
        }}
      >
        MISPL Agent
      </div>
      <div style={{ position: "absolute", top: 26, right: 24 }}>
        <BetaBadge />
      </div>
      <div style={{ position: "relative" }}>
        <h1 style={{ fontSize: 32, marginBottom: 12 }}>Assistant MISPL pour GLIMS</h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 15, maxWidth: 400, margin: "0 auto 16px" }}>
          Réponses sourcées depuis la documentation MISPL — sans hallucination.
        </p>
        <p style={{ color: "var(--ink-soft)", fontSize: 12.5, marginBottom: 28 }}>
          Sourcé documentation officielle · Zéro hallucination · Mode DSI / Technicien
        </p>
        <Link
          href="/login"
          style={{
            display: "inline-block",
            background: "var(--accent-solid)",
            color: "var(--accent-solid-text)",
            fontFamily: "var(--sans)",
            fontSize: 14,
            fontWeight: 500,
            padding: "12px 28px",
            borderRadius: 10,
            textDecoration: "none",
          }}
        >
          Se connecter
        </Link>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 3: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): polish landing page (réassurance, halo, bouton thématisé)"
```

---

### Task 5: Polish UI du chat — bulles, empty state, focus des champs

**Files:**
- Modify: `frontend/app/globals.css` (ajouts en fin de fichier)
- Modify: `frontend/components/ChatMessage.tsx` (issu de la Task 2)
- Modify: `frontend/components/EmptyState.tsx`

**Interfaces:**
- Consumes : `ChatMessage.tsx` tel que produit par la Task 2 ; tokens `--accent-text`, `--shadow`, `--accent-soft`, `--accent` (Task 1).

- [ ] **Step 1: Ajouter les règles de focus et `.example-card` à `globals.css`**

Ajouter à la fin du fichier `frontend/app/globals.css` :

```css

input:focus,
textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.example-card {
  background: transparent;
  color: var(--accent-text);
  border: 1px solid var(--accent-text);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.example-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow);
  opacity: 1;
}
```

- [ ] **Step 2: Resserrer l'espacement et ajouter l'ombre des bulles dans `ChatMessage.tsx`**

Dans `frontend/components/ChatMessage.tsx` (tel que produit par la Task 2), remplacer les deux occurrences de `margin: "12px 0"` (une dans le wrapper de la bulle utilisateur, une dans le wrapper de la réponse assistant) par `margin: "16px 0"`.

Puis, dans le style de la bulle utilisateur, remplacer :

```tsx
        <span
          style={{
            display: "inline-block",
            background: "var(--accent-solid)",
            color: "var(--accent-solid-text)",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "80%",
            fontSize: 14,
          }}
        >
```

par :

```tsx
        <span
          style={{
            display: "inline-block",
            background: "var(--accent-solid)",
            color: "var(--accent-solid-text)",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "72%",
            fontSize: 14,
            boxShadow: "var(--shadow)",
          }}
        >
```

- [ ] **Step 3: Basculer les boutons d'exemple de `EmptyState.tsx` sur `.example-card`**

Dans `frontend/components/EmptyState.tsx`, remplacer :

```tsx
          <button key={ex} className="ghost" onClick={() => onPick(ex)} style={{ fontSize: 13 }}>
```

par :

```tsx
          <button key={ex} className="example-card" onClick={() => onPick(ex)} style={{ fontSize: 13 }}>
```

- [ ] **Step 4: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 5: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 6: Vérification manuelle dans le navigateur**

Avec le backend (`uvicorn api.main:app --port 8000`) et le frontend (`npm run dev`, port 3000) lancés, connecté avec un compte existant :

1. Ouvrir le menu compte (nom + avatar en haut à droite du chat) → le panneau s'affiche avec 3 pastilles de couleur et le bouton Déconnexion.
2. Cliquer sur la pastille violette → tous les boutons pleins (Envoyer, Se connecter sur la landing si on y retourne), les bulles utilisateur, les avatars, les bordures de champ au focus passent au violet `#5F4D84` avec texte blanc lisible.
3. Cliquer sur la pastille orange → mêmes éléments passent en orange `#D66E0B`, mais avec **texte foncé** sur les fonds pleins (pas blanc).
4. Rafraîchir la page (F5) → le thème choisi reste appliqué immédiatement, sans flash de la couleur verte par défaut.
5. Se déconnecter puis revenir sur la landing page (`/`) → le bouton "Se connecter" reflète le thème choisi, le bandeau de réassurance et le halo derrière le titre sont visibles.
6. Dans le chat, vérifier que l'icône assistant (bulles de réponse + indicateur "Recherche dans la documentation...") affiche bien un robot dessiné (pas juste des initiales), dans la teinte pâle du thème actif sur fond sombre.
7. Survoler un des 4 boutons d'exemple de question (état vide du chat) → légère élévation avec ombre.
8. Cliquer dans le champ de saisie de la question → contour de couleur du thème visible (au lieu du gris neutre par défaut).

- [ ] **Step 7: Commit**

```bash
git add frontend/app/globals.css frontend/components/ChatMessage.tsx frontend/components/EmptyState.tsx
git commit -m "feat(frontend): polish UI du chat (bulles, empty state, focus des champs)"
```
