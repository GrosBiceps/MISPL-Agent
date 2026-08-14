# Polish UI, icône assistant et sélecteur de thème — Design

## Contexte

Depuis les chantiers précédents (auth, migration frontend, polish-UI initial,
historique de sessions), l'application MISPL Agent a une base fonctionnelle
en Next.js, style « Quiet Luxury » (tokens CSS dans `frontend/app/globals.css`,
typographie serif pour les titres). Ce chantier regroupe quatre demandes
utilisateur groupées dans un même message : améliorer la landing page,
améliorer l'UI générale du chat, remplacer l'icône assistant, et ajouter un
sélecteur de couleur de thème (vert actuel / violet / orange).

**Investigation préalable** : l'icône assistant actuelle
(`frontend/lib/avatar.ts::ASSISTANT_AVATAR`) n'est pas cassée — c'est un SVG
data-URI valide, identique à celui de l'ancien `app.py` Streamlit (cercle
sombre + initiales « AI »). Ce n'est donc pas un bug de rendu mais un
décalage d'attente : l'utilisateur veut une vraie icône de robot illustrée,
pas des initiales dans un cercle.

## A. Icône assistant

Un nouveau composant SVG inline représentant un robot simple (traits fins,
cohérent avec le style épuré), remplaçant `ASSISTANT_AVATAR` partout où il
est utilisé aujourd'hui : `frontend/components/ChatMessage.tsx` (bulles de
réponse) et `frontend/components/ThinkingIndicator.tsx` (indicateur de
chargement). L'icône suit la couleur du thème actif (utilise
`var(--accent)` comme couleur de trait/fond au lieu d'une couleur fixe).

## B. Système de thème (3 couleurs)

**Mécanisme** : attribut `data-theme="green" | "purple" | "orange"` sur
`<html>` (le vert reste le défaut si l'attribut est absent — pas de
migration nécessaire pour les utilisateurs existants). Chaque thème définit
un bloc de tokens sous `:root[data-theme="..."]` dans `globals.css`. Un
script inline dans `frontend/app/layout.tsx` (exécuté avant l'hydratation
React) lit `localStorage.getItem("theme")` et pose l'attribut
`data-theme` sur `<html>` immédiatement, pour éviter un flash de la
mauvaise couleur au chargement — même principe que la persistance du repli
de sidebar déjà en place (chantier historique de sessions).

**Tokens par thème** (remplacent l'usage actuel de `--accent`/`--accent-soft`
codés en dur, et les couleurs hexadécimales dispersées dans les composants) :

| Thème | `--accent` (bordures/icônes) | `--accent-solid` (fond bouton) | `--accent-solid-text` (texte sur bouton) | `--accent-soft` (fond badge/hover) |
|---|---|---|---|---|
| 🟢 green (défaut) | `#6f7d6a` | `#5a6656` | `#ffffff` | `#eef0ec` |
| 🟣 purple | `#5F4D84` | `#5F4D84` | `#ffffff` | `#eeebf4` |
| 🟠 orange | `#D66E0B` | `#D66E0B` | `#1a1a1a` (`var(--ink)`) | `#faecdc` |

**Justification du choix texte foncé pour l'orange** : contraste WCAG AA
vérifié pour chaque paire (formule de luminance relative standard) :
- Texte blanc sur `#5a6656` (vert) : 6,05:1 — ✅
- Texte blanc sur `#5F4D84` (violet) : 7,29:1 — ✅
- Texte blanc sur `#D66E0B` (orange) : 3,44:1 — ❌ (sous le seuil 4,5:1)
- Texte `#1a1a1a` sur `#D66E0B` (orange) : 5,04:1 — ✅

Décision validée avec l'utilisateur : garder `#D66E0B` exact comme couleur
de fond pour le thème orange, et utiliser `--accent-solid-text: var(--ink)`
au lieu de blanc pour ce thème uniquement.

**Note sur une limite pré-existante non corrigée** : `.card code` utilise
déjà `color: var(--accent)` sur fond `var(--accent-soft)`
(`globals.css:118-124`), ce qui pour le vert actuel donne ~3,80:1 — sous le
seuil AA, mais déjà en production avant ce chantier. Les thèmes violet et
orange héritent de la même règle existante avec la même limite (pas une
régression introduite par ce chantier, un défaut préexistant qui n'est pas
dans le périmètre de cette demande — à traiter séparément si besoin).

**Composants à migrer vers les tokens de thème** (au lieu de couleurs
codées en dur) :
- `frontend/app/page.tsx:41` — bouton « Se connecter » (`#5a6656` → `var(--accent-solid)` / `var(--accent-solid-text)`)
- `frontend/components/ChatMessage.tsx:36` — fond de bulle utilisateur (`#5a6656` → tokens de thème)
- `frontend/components/ChatMessage.tsx:46` — avatar utilisateur (`#6f7d6a` → `var(--accent)`)
- `frontend/app/globals.css` — règle globale `button { background: var(--accent); }` (ligne 54) → `var(--accent-solid)` + `color: var(--accent-solid-text)` (actuellement `color: #fff` fixe en ligne 55)

**État React** : un contexte `ThemeContext` (`frontend/lib/theme-context.tsx`)
expose `{ theme: "green" | "purple" | "orange", setTheme: (t) => void }`.
`setTheme` met à jour `localStorage` ET pose l'attribut `data-theme` sur
`document.documentElement` directement (pas de re-render de toute l'arborescence
nécessaire — c'est du CSS pur qui réagit à l'attribut). Le provider englobe
l'application dans `frontend/app/layout.tsx`.

## C. Menu compte

Nouveau composant `frontend/components/AccountMenu.tsx`, remplaçant le nom
d'utilisateur en texte brut + bouton « Déconnexion » actuels dans le header
de `frontend/app/chat/page.tsx`. Comportement :
- Un bouton déclencheur (avatar initiales + nom) ouvre un panneau `.card`
  positionné en dessous (`position: absolute`).
- Contenu du panneau : sélecteur de thème (3 pastilles de couleur cliquables,
  celle active visuellement entourée d'un anneau), séparateur, bouton
  « Déconnexion ».
- Fermeture au clic en dehors du panneau (listener `mousedown` sur
  `document`) ou à la touche `Échap`.
- Le déclencheur utilise `getInitials`/`svgAvatar` déjà présents dans
  `frontend/lib/avatar.ts` — pas de nouvelle logique d'avatar utilisateur.

`frontend/app/chat/page.tsx` : le `<p>` affichant `user.display_name` sous
le titre est supprimé (le nom vit désormais uniquement dans `AccountMenu`,
supprimant la duplication actuelle nom-affiché-deux-fois entre header et
bas de sidebar).

## D. Page d'accueil (landing)

`frontend/app/page.tsx`, structure « centrée minimale » conservée, avec :
- Un bandeau de 3 points de réassurance en texte seul sous la tagline :
  « Sourcé depuis la documentation officielle », « Zéro hallucination »,
  « Mode DSI / Technicien » — disposés horizontalement, séparés par un
  point médian (`·`), taille de police réduite (`var(--ink-soft)`, 13px),
  pas d'icônes.
- Le bouton « Se connecter » utilise les tokens de thème (`var(--accent-solid)`
  / `var(--accent-solid-text)`) au lieu de `#5a6656` fixe — lit le thème
  déjà stocké en `localStorage` via le même script de `layout.tsx` que le
  reste de l'app (fonctionne même avant connexion, puisque c'est une
  préférence de navigateur, pas de compte).
- Un halo radial très subtil derrière le titre (`background: radial-gradient`
  centré, utilisant `var(--accent-soft)` à faible opacité), pour casser le
  vide visuel sans ajouter d'éléments graphiques lourds.

## E. Polish de l'UI du chat

- **Bulles de message** (`ChatMessage.tsx`) : `box-shadow: var(--shadow)`
  ajouté aux bulles (actuellement seules les cartes `.card` en ont une),
  marge verticale augmentée entre tours de conversation (12px → 16px),
  `max-width` des bulles resserré (actuellement 80% de la largeur de la
  colonne de chat — passe à 72%) pour améliorer la lisibilité des réponses
  longues.
- **En-tête de conversation** (`frontend/app/chat/page.tsx`) : remplace le
  `<p>` nom d'utilisateur + bouton ghost « Déconnexion » par `AccountMenu`
  (section C).
- **État vide** (`EmptyState.tsx`) : les boutons d'exemple passent de
  `button.ghost` statique à une variante avec légère élévation au survol
  (`transform: translateY(-1px)` + `box-shadow: var(--shadow)`,
  transition 0.15s) — nouvelle classe `.example-card` dans `globals.css`,
  remplaçant `className="ghost"` sur ces boutons spécifiquement.
- **Zone de saisie** : le bouton « Envoyer » suit désormais
  `var(--accent-solid)`/`var(--accent-solid-text)` (hérité automatiquement
  du changement de la règle globale `button` en section B — pas de
  modification supplémentaire nécessaire). Focus des champs texte
  (`input:focus`) : nouvelle règle `border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);`
  dans `globals.css`, remplaçant l'absence actuelle de style de focus visible.

Portée explicitement exclue : la structure et le comportement de la sidebar
d'historique (chantier précédent) ne sont pas modifiés — seules ses couleurs
héritent des tokens de thème déjà utilisés (`var(--accent)`,
`var(--accent-soft)`), aucun changement de layout ou de logique.

## Tests

Comme pour les chantiers frontend précédents, aucun framework de test n'est
configuré dans ce projet (pas de Jest/Vitest). Vérification via
`npx tsc --noEmit` et `npm run build`, plus vérification manuelle en
navigateur (bascule des 3 thèmes, persistance au rechargement, contraste
visuel des boutons par thème, ouverture/fermeture du menu compte, icône
robot visible dans les bulles et l'indicateur de chargement).
