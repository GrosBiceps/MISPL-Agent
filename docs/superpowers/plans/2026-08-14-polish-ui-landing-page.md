# Polish UI + Landing page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une landing page publique, un badge Beta, un badge de certitude visuel, un bouton copier sur les blocs de code, et une zone de saisie sticky au frontend MISPL Agent — sans toucher au backend ni au style Quiet Luxury déjà validé.

**Architecture:** Modifications ciblées dans `frontend/` uniquement (composants React + CSS). Aucun changement d'API, aucune nouvelle dépendance npm (react-markdown déjà installé, sa prop `components` suffit pour le rendu personnalisé des blocs de code).

**Tech Stack:** Next.js (App Router, TypeScript), react-markdown (déjà en place), CSS pur (tokens Quiet Luxury existants).

## Global Constraints

- Style Quiet Luxury conservé — titres serif (`var(--serif)`), corps sans-serif (`var(--sans)`) — **aucun changement de typographie**
- Largeur du conteneur de chat (780px) déjà correcte — **ne pas la modifier**
- Pas d'auto-inscription — la landing ne propose qu'un bouton « Se connecter », jamais de lien « créer un compte »
- Le badge de certitude est un traitement **purement côté présentation** — `ChatResponse.response` reste une chaîne Markdown brute côté API, aucun changement backend
- Pas de suite de tests automatisés frontend dans ce chantier (décision actée) — vérification manuelle documentée à chaque tâche concernée, plus `npm run build` comme garde-fou (erreurs TypeScript/build)
- Couleurs du badge de certitude imposées (validées visuellement) : Certain = vert sauge (`var(--accent)` / `var(--accent-soft)`), Probable = ambre (`#a3791f` / `#f7f1e3` / bordure `#d9b45c`), À vérifier = terracotta (`#a8584f` / `#f6ece9`)

---

## Task 1: Extraction du niveau de certitude + composant Badge Beta

**Files:**
- Create: `frontend/lib/certainty.ts`
- Create: `frontend/components/BetaBadge.tsx`

**Interfaces:**
- Produces: `extractCertainty(markdown: string) -> { level: "certain" | "probable" | "check" | null, cleanedContent: string }`, composant `BetaBadge` (aucune prop)

- [ ] **Step 1: Implémenter `frontend/lib/certainty.ts`**

```typescript
export type CertaintyLevel = "certain" | "probable" | "check" | null;

export interface CertaintyExtraction {
  level: CertaintyLevel;
  cleanedContent: string;
}

const SECTION_HEADING = /^##\s*Niveau de certitude\s*$/im;

// Détecte la section "## Niveau de certitude" du Markdown de réponse
// (format imposé par CLAUDE.md), extrait le niveau (✅/⚠️/🔬) et retire
// la section du texte pour éviter un affichage en double avec le badge.
export function extractCertainty(markdown: string): CertaintyExtraction {
  const headingMatch = SECTION_HEADING.exec(markdown);
  if (!headingMatch) {
    return { level: null, cleanedContent: markdown };
  }

  const sectionStart = headingMatch.index;
  const afterHeading = markdown.slice(sectionStart + headingMatch[0].length);
  const nextHeadingMatch = /^##\s/m.exec(afterHeading);
  const sectionEnd = nextHeadingMatch
    ? sectionStart + headingMatch[0].length + nextHeadingMatch.index
    : markdown.length;

  const sectionBody = markdown.slice(sectionStart, sectionEnd);

  let level: CertaintyLevel = null;
  if (sectionBody.includes("✅")) level = "certain";
  else if (sectionBody.includes("⚠️")) level = "probable";
  else if (sectionBody.includes("🔬")) level = "check";

  if (level === null) {
    return { level: null, cleanedContent: markdown };
  }

  const cleanedContent = (markdown.slice(0, sectionStart) + markdown.slice(sectionEnd)).trim();
  return { level, cleanedContent };
}
```

- [ ] **Step 2: Vérification manuelle de la logique (pas de suite de tests frontend dans ce chantier)**

Crée temporairement un fichier `frontend/scratch-check.mjs` (jamais committé) pour valider la regex avant de l'utiliser dans l'UI :

```javascript
// scratch-check.mjs — à supprimer après vérification, ne pas committer
function extractCertainty(markdown) {
  const SECTION_HEADING = /^##\s*Niveau de certitude\s*$/im;
  const headingMatch = SECTION_HEADING.exec(markdown);
  if (!headingMatch) return { level: null, cleanedContent: markdown };
  const sectionStart = headingMatch.index;
  const afterHeading = markdown.slice(sectionStart + headingMatch[0].length);
  const nextHeadingMatch = /^##\s/m.exec(afterHeading);
  const sectionEnd = nextHeadingMatch
    ? sectionStart + headingMatch[0].length + nextHeadingMatch.index
    : markdown.length;
  const sectionBody = markdown.slice(sectionStart, sectionEnd);
  let level = null;
  if (sectionBody.includes("✅")) level = "certain";
  else if (sectionBody.includes("⚠️")) level = "probable";
  else if (sectionBody.includes("🔬")) level = "check";
  if (level === null) return { level: null, cleanedContent: markdown };
  const cleanedContent = (markdown.slice(0, sectionStart) + markdown.slice(sectionEnd)).trim();
  return { level, cleanedContent };
}

const sample = `## Contexte GLIMS
Bla bla.

## Code MISPL
\`\`\`mispl
RETURN Substr("abc", 1, 2);
\`\`\`

## Niveau de certitude
✅ **Certain** — fonction documentée, syntaxe confirmée

## Notes techniques
Aucun risque particulier.`;

const result = extractCertainty(sample);
console.log("level:", result.level); // attendu: "certain"
console.log("--- cleanedContent ---");
console.log(result.cleanedContent); // attendu: pas de section "Niveau de certitude"
console.assert(result.level === "certain", "ECHEC: level devrait être certain");
console.assert(!result.cleanedContent.includes("Niveau de certitude"), "ECHEC: section pas retirée");
console.log("OK — tous les asserts sont passés si aucun message ECHEC ci-dessus");
```

Run: `cd frontend && node scratch-check.mjs`
Expected: `level: certain`, pas de message `ECHEC`, la section "Niveau de certitude" absente de `cleanedContent`

Supprime `scratch-check.mjs` une fois vérifié (`rm frontend/scratch-check.mjs`).

- [ ] **Step 3: Implémenter `frontend/components/BetaBadge.tsx`**

```tsx
export default function BetaBadge() {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: "var(--accent)",
        background: "var(--accent-soft)",
        border: "1px solid var(--line)",
        padding: "3px 10px",
        borderRadius: 999,
      }}
    >
      Beta
    </span>
  );
}
```

- [ ] **Step 4: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi, aucune erreur TypeScript (ces deux fichiers ne sont pas encore consommés ailleurs, donc aucun changement de rendu à ce stade)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/certainty.ts frontend/components/BetaBadge.tsx
git commit -m "feat(frontend): extraction niveau de certitude + composant BetaBadge"
```

---

## Task 2: Bouton Copier sur les blocs de code

**Files:**
- Create: `frontend/components/CodeBlock.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Produces: composant `CodeBlock` — à utiliser comme override du rendu `pre` de `react-markdown` (prop `children` = les éléments React que react-markdown place normalement dans `<pre>`, typiquement un `<code>`)

- [ ] **Step 1: Implémenter `frontend/components/CodeBlock.tsx`**

```tsx
"use client";

import { useState, isValidElement, ReactNode } from "react";

function extractText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (isValidElement(node)) {
    const props = node.props as { children?: ReactNode };
    return extractText(props.children);
  }
  return "";
}

interface Props {
  children?: ReactNode;
}

export default function CodeBlock({ children }: Props) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const text = extractText(children);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Presse-papiers indisponible (contexte non sécurisé, permission refusée)
      // — pas d'action, le bouton reste "Copier".
    }
  }

  return (
    <div className="code-block-wrapper">
      <button type="button" className="copy-btn" onClick={handleCopy}>
        {copied ? "Copié ✓" : "Copier"}
      </button>
      <pre>{children}</pre>
    </div>
  );
}
```

- [ ] **Step 2: Ajouter les styles dans `frontend/app/globals.css`**

Ajouter à la fin du fichier :

```css
.code-block-wrapper {
  position: relative;
}
.code-block-wrapper .copy-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 11px;
  color: #9db4ac;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  padding: 4px 9px;
  border-radius: 6px;
  cursor: pointer;
}
.code-block-wrapper .copy-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  opacity: 1;
}
```

(La règle `.code-block-wrapper .copy-btn` a une spécificité CSS supérieure à la règle globale `button` déjà présente dans ce fichier — le bouton ne prendra donc pas le fond sauge par défaut.)

- [ ] **Step 3: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi (composant pas encore branché dans `ChatMessage.tsx`, donc pas de changement de rendu visible à ce stade — la Task 3 le branche)

- [ ] **Step 4: Commit**

```bash
git add frontend/components/CodeBlock.tsx frontend/app/globals.css
git commit -m "feat(frontend): composant CodeBlock avec bouton copier"
```

---

## Task 3: Intégration badge de certitude + bouton copier dans ChatMessage

**Files:**
- Modify: `frontend/components/ChatMessage.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes: `extractCertainty` (Task 1, `frontend/lib/certainty.ts`), `CodeBlock` (Task 2, `frontend/components/CodeBlock.tsx`)

- [ ] **Step 1: Ajouter les styles du badge de certitude dans `frontend/app/globals.css`**

Ajouter à la fin du fichier :

```css
.cert-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 999px;
  margin-bottom: 10px;
}
.cert-certain {
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid var(--accent);
}
.cert-probable {
  background: #f7f1e3;
  color: #a3791f;
  border: 1px solid #d9b45c;
}
.cert-check {
  background: #f6ece9;
  color: #a8584f;
  border: 1px solid #a8584f;
}
```

- [ ] **Step 2: Modifier `frontend/components/ChatMessage.tsx`**

Le fichier actuel importe déjà `ReactMarkdown`, `SourceOut`, `ASSISTANT_AVATAR`, `svgAvatar`. Ajouter les nouveaux imports et la logique d'extraction. Voici le fichier complet après modification :

```tsx
import ReactMarkdown from "react-markdown";
import { SourceOut } from "../lib/api";
import { ASSISTANT_AVATAR, svgAvatar } from "../lib/avatar";
import { extractCertainty } from "../lib/certainty";
import CodeBlock from "./CodeBlock";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
  userInitials?: string;
}

const avatarStyle = { width: 32, height: 32, borderRadius: "50%", flexShrink: 0 } as const;

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
            background: "var(--accent)",
            color: "#fff",
            padding: "10px 14px",
            borderRadius: "12px 12px 3px 12px",
            maxWidth: "80%",
            fontSize: 14,
          }}
        >
          {content}
        </span>
        <img src={svgAvatar("#6f7d6a", "#ffffff", userInitials || "?")} alt="" style={avatarStyle} />
      </div>
    );
  }

  const { level, cleanedContent } = extractCertainty(content);

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "12px 0" }}>
      <img src={ASSISTANT_AVATAR} alt="" style={avatarStyle} />
      <div style={{ flex: 1, minWidth: 0 }}>
        {warning && warning.length > 0 && (
          <div className="warning-banner">
            ⚠️ Donnée potentiellement sensible détectée ({warning.join(", ")})
          </div>
        )}
        <div className="card" style={{ fontSize: 14, lineHeight: 1.6 }}>
          {level && <span className={`cert-badge ${CERTAINTY_CLASS[level]}`}>{CERTAINTY_LABEL[level]}</span>}
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

- [ ] **Step 3: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi, aucune erreur TypeScript

- [ ] **Step 4: Vérification manuelle**

1. Lancer les deux serveurs (`.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000` depuis la racine, et `cd frontend && npm run dev`)
2. Se connecter sur `http://localhost:3000/login`
3. Poser une question qui produit une réponse avec du code MISPL (ex: "Comment utiliser Substr ?")
4. Vérifier : un badge coloré (vert si le niveau est "Certain") apparaît en haut de la réponse, avant le texte ; la section "## Niveau de certitude" n'apparaît PAS une deuxième fois dans le corps du texte ; un bouton "Copier" apparaît en haut à droite du bloc de code noir ; cliquer dessus change le texte en "Copié ✓" pendant ~1.5s puis colle bien le code (vérifier en collant dans un éditeur)
5. Si le modèle répond avec un niveau différent (⚠️ ou 🔬) lors d'une autre question, vérifier que la couleur du badge change en conséquence (ambre / terracotta)

- [ ] **Step 5: Commit**

```bash
git add frontend/components/ChatMessage.tsx frontend/app/globals.css
git commit -m "feat(frontend): badge de certitude + bouton copier dans les réponses"
```

---

## Task 4: Landing page

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `BetaBadge` (Task 1, `frontend/components/BetaBadge.tsx`)

- [ ] **Step 1: Remplacer `frontend/app/page.tsx`**

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
      }}
    >
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
      <h1 style={{ fontSize: 32, marginBottom: 12 }}>Assistant MISPL pour GLIMS</h1>
      <p style={{ color: "var(--ink-soft)", fontSize: 15, maxWidth: 400, margin: "0 0 28px" }}>
        Réponses sourcées depuis la documentation MISPL — sans hallucination.
      </p>
      <Link
        href="/login"
        style={{
          display: "inline-block",
          background: "var(--accent)",
          color: "#fff",
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
    </main>
  );
}
```

- [ ] **Step 2: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi. Vérifier dans la sortie que la route `/` est bien listée comme page statique (elle ne doit plus déclencher de redirection server-side)

- [ ] **Step 3: Vérification manuelle**

1. `cd frontend && npm run dev`
2. Ouvrir `http://localhost:3000/` **sans être connecté** — vérifier que la landing s'affiche (logo en haut à gauche, badge Beta en haut à droite, titre, phrase, bouton), et qu'il n'y a **plus** de redirection automatique vers `/chat` ou `/login`
3. Cliquer sur "Se connecter" — vérifier l'arrivée sur `/login`
4. Se connecter, puis revenir sur `http://localhost:3000/` — vérifier que la landing s'affiche toujours (pas de redirection automatique vers `/chat` même connecté, comportement attendu : la landing est une page d'accueil neutre, l'utilisateur clique lui-même pour continuer)

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): landing page publique (remplace la redirection auto vers /chat)"
```

---

## Task 5: Zone de saisie sticky + badge Beta dans l'en-tête du chat

**Files:**
- Modify: `frontend/app/chat/page.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes: `BetaBadge` (Task 1, `frontend/components/BetaBadge.tsx`)
- Produces: rien de consommé par une tâche ultérieure (dernière tâche du chantier)

- [ ] **Step 1: Ajouter le style sticky dans `frontend/app/globals.css`**

Ajouter à la fin du fichier :

```css
.sticky-input-bar {
  position: sticky;
  bottom: 0;
  background: var(--bg);
  padding: 16px 0 20px;
}
```

- [ ] **Step 2: Modifier `frontend/app/chat/page.tsx`**

Trois changements dans ce fichier :

**a) Importer `BetaBadge`** — ajouter en haut du fichier, avec les autres imports de composants :
```tsx
import BetaBadge from "../../components/BetaBadge";
```

**b) Ajouter le badge à côté du titre** — remplacer :
```tsx
        <div>
          <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
          <p style={{ color: "var(--ink-soft)", fontSize: 13 }}>{user.display_name}</p>
        </div>
```
par :
```tsx
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
            <BetaBadge />
          </div>
          <p style={{ color: "var(--ink-soft)", fontSize: 13 }}>{user.display_name}</p>
        </div>
```

**c) Rendre la zone de saisie sticky et réduire le padding de bas de page devenu redondant** — remplacer la balise `<main>` d'ouverture :
```tsx
    <main style={{ maxWidth: 780, margin: "0 auto", padding: "2rem 1.5rem 6rem" }}>
```
par (le padding bas passe de `6rem` à `1rem` — la barre sticky gère désormais son propre espacement, l'ancien padding compensait une barre non-sticky) :
```tsx
    <main style={{ maxWidth: 780, margin: "0 auto", padding: "2rem 1.5rem 1rem" }}>
```

Puis remplacer le bloc de saisie en fin de fichier :
```tsx
      <div className="card" style={{ marginTop: 20 }}>
        <label style={{ display: "block", fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
          Contexte labo (optionnel)
        </label>
        <input
          value={labContext}
          onChange={(e) => setLabContext(e.target.value)}
          placeholder="ex: Analyseur Cobas c702, tube EDTA, unités SI"
          style={{ marginBottom: 12 }}
        />
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk(question);
          }}
          style={{ display: "flex", gap: 8 }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Posez votre question MISPL..."
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={loading}>
            {loading ? "..." : "Envoyer"}
          </button>
        </form>
      </div>
```
par :
```tsx
      <div className="sticky-input-bar">
        <div className="card">
          <label style={{ display: "block", fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
            Contexte labo (optionnel)
          </label>
          <input
            value={labContext}
            onChange={(e) => setLabContext(e.target.value)}
            placeholder="ex: Analyseur Cobas c702, tube EDTA, unités SI"
            style={{ marginBottom: 12 }}
          />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(question);
            }}
            style={{ display: "flex", gap: 8 }}
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Posez votre question MISPL..."
              style={{ flex: 1 }}
            />
            <button type="submit" disabled={loading}>
              {loading ? "..." : "Envoyer"}
            </button>
          </form>
        </div>
      </div>
```

- [ ] **Step 3: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi, aucune erreur TypeScript

- [ ] **Step 4: Vérification manuelle complète du chantier**

Avec les deux serveurs lancés :

1. Se connecter, aller sur `/chat` — vérifier que le badge "Beta" apparaît à côté de "Assistant MISPL" dans l'en-tête
2. Poser plusieurs questions successives jusqu'à ce que la conversation dépasse la hauteur de l'écran — vérifier que la zone de saisie (contexte labo + input + bouton Envoyer) **reste visible en bas de l'écran** pendant le défilement, ne se fait jamais recouvrir par les messages, et que les messages ne passent jamais dessous
3. Vérifier l'alignement vertical des avatars : sur un message assistant, l'avatar (cercle "AI") doit être aligné avec le haut de la carte de réponse — pas de décalage visuel notable. Idem côté utilisateur (avatar avec initiales aligné avec le haut de la bulle)
4. Vérifier la lisibilité du texte blanc sur fond sauge de la bulle utilisateur — si le contraste semble insuffisant à l'œil (texte difficile à lire), foncer localement le fond de la bulle utilisateur uniquement (dans `ChatMessage.tsx`, remplacer `background: "var(--accent)"` par `background: "#5a6656"` pour ce cas précis) — **ne pas modifier le token global `--accent`**, qui est utilisé ailleurs (boutons, badges) où le contraste actuel est correct

- [ ] **Step 5: Commit**

```bash
git add frontend/app/chat/page.tsx frontend/app/globals.css
git commit -m "feat(frontend): zone de saisie sticky + badge Beta dans l'en-tête du chat"
```
