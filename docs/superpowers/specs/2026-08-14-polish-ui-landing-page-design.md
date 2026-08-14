# Polish UI + Landing page — MISPL Agent

Date : 2026-08-14
Statut : approuvé, prêt pour plan d'implémentation

## Contexte

Le chantier A (fondations frontend) a livré un frontend Next.js fonctionnel
(login + chat) en parité avec l'ancien `app.py`. Un retour utilisateur a
listé une série d'améliorations UI/UX pour rapprocher l'outil d'un vrai
produit commercial. Cette liste couvrait plusieurs sous-systèmes de tailles
très différentes ; ce document ne couvre QUE la partie faisable sans
dépendance à une fonctionnalité non construite.

**Décomposition actée en amont** (non rediscutée ici) :
- **Ce chantier** : landing page, badge Beta, badge de certitude, bouton
  copier sur les blocs de code, zone de saisie sticky, nettoyage
  alignement/contraste
- **Hors périmètre, chantiers séparés futurs** : historique de sessions en
  sidebar (dépend d'un chantier non construit), menu de statistiques de
  consommation de tokens (aucun tracking d'usage n'existe côté backend),
  bouton d'attachement fichier/capture + OCR Tesseract (fonctionnalité
  entièrement nouvelle, non scopée)

**Décision de conception actée** : le style **Quiet Luxury** (titres serif,
corps sans-serif Inter) est **conservé**, malgré une demande initiale de
tout basculer en sans-serif — c'est l'identité visuelle qui différencie
l'outil d'un chatbot générique, décision déjà validée lors du chantier de
migration frontend.

**Validé via le compagnon visuel de brainstorming** : layout de landing
page « A — centré minimal » (logo haut-gauche, badge Beta haut-droite,
titre + une phrase + bouton), et le style du badge de certitude (pill
colorée par niveau : vert/ambre/rouge) + bouton copier discret en haut à
droite des blocs de code.

## Périmètre

**Inclus :**
- Nouvelle landing page publique (`/`) — remplace la redirection
  automatique actuelle vers `/chat`
- Badge « Beta » (composant réutilisé landing + en-tête `/chat`)
- Badge de certitude visuel, extrait du Markdown de réponse
- Bouton « Copier » sur les blocs de code MISPL
- Zone de saisie (contexte labo + input) fixée en bas de l'écran (sticky)
- Nettoyage alignement des avatars (ajoutés lors du chantier précédent) et
  contraste des bulles utilisateur si nécessaire

**Explicitement hors périmètre :**
- Historique de sessions sidebar
- Menu stats de consommation de tokens
- Bouton d'attachement fichier + OCR
- Largeur du conteneur de chat : déjà à 780px, dans la fourchette demandée
  (768-800px) — **aucun changement nécessaire**, vérifié avant ce chantier
- Typographie : **pas de changement** — Quiet Luxury conservé (voir
  décision actée ci-dessus)

## Landing page

Nouvelle page `frontend/app/page.tsx`, remplace la redirection actuelle
`redirect("/chat")`. Layout centré minimal (validé visuellement) :
- Logo texte « MISPL Agent » (serif, ancré en haut à gauche)
- Badge « Beta » (ancré en haut à droite)
- Titre principal (serif) : « Assistant MISPL pour GLIMS »
- Une seule phrase d'accroche (sans-serif, `--ink-soft`) : le positionnement
  du produit en une ligne, pas de paragraphe marketing
- Bouton « Se connecter » → `/login`

Contenu centré verticalement et horizontalement, `max-width` cohérent avec
le reste de l'app (~780px pour le bloc de contenu, mais la page elle-même
peut occuper toute la largeur/hauteur de l'écran).

Pas de logique d'auto-inscription ni de lien « créer un compte » — cohérent
avec la politique actée au chantier auth (comptes créés uniquement par un
admin). Si un visiteur sans compte arrive sur `/login`, rien de spécifique
à ajouter ici — c'est un besoin distinct, non demandé dans ce chantier.

## Badge Beta

Composant `frontend/components/BetaBadge.tsx` — pill simple (texte « Beta »
en majuscules, taille 11px, fond `--accent-soft`, bordure `--line`, texte
`--accent`). Utilisé sur la landing (à côté du logo) et dans l'en-tête de
`/chat` (à côté de « Assistant MISPL »).

## Badge de certitude

**Problème actuel** : le niveau de certitude (`✅ Certain` / `⚠️ Probable` /
`🔬 À vérifier`) fait partie du corps Markdown de la réponse LLM, sous une
section `## Niveau de certitude` (format imposé par `CLAUDE.md` — non
modifiable ici, c'est une contrainte du prompt système). Il se noie dans le
reste du texte.

**Traitement côté frontend** (`frontend/components/ChatMessage.tsx`) :
1. Avant le rendu Markdown, une fonction extrait la section `## Niveau de
   certitude` (recherche du titre, capture du contenu jusqu'au prochain
   `##` ou la fin du texte) et y détecte lequel des 3 marqueurs
   (`✅ Certain`, `⚠️ Probable`, `🔬 À vérifier`) est présent.
2. Si trouvé : affiche un badge pill coloré en haut du message (vert pour
   Certain, ambre pour Probable, rouge/terracotta pour À vérifier — mêmes
   codes couleur que le badge de certitude testé visuellement).
3. La section `## Niveau de certitude` est retirée du texte transmis à
   `ReactMarkdown` (regex de suppression), pour ne pas l'afficher deux fois.
4. Si aucun marqueur n'est trouvé (réponse ne suivant pas le format —
   possible avec certains modèles malgré la consigne), aucun badge n'est
   affiché et le Markdown est rendu tel quel, sans section retirée.

Ce traitement est purement côté présentation — aucun changement backend,
`ChatResponse.response` reste une chaîne Markdown brute.

## Bouton Copier sur les blocs de code

`ChatMessage.tsx` personnalise le rendu des blocs de code de
`react-markdown` (composant `pre`/`code` custom) pour ajouter un bouton
« Copier » positionné en haut à droite de chaque bloc ` ```mispl ` (ou tout
bloc de code générique). Au clic : `navigator.clipboard.writeText()` avec
le contenu texte brut du bloc, feedback visuel bref (le texte du bouton
passe à « Copié ✓ » pendant ~1.5s puis revient à « Copier »).

## Zone de saisie sticky

Le bloc `<div className="card">` contenant le contexte labo et l'input
(actuellement en flux normal en bas de `frontend/app/chat/page.tsx`) passe
en position fixée : `position: sticky; bottom: 0` avec un fond opaque
(`--bg`) et un padding suffisant pour ne jamais chevaucher le dernier
message pendant le scroll.

## Nettoyage alignement / contraste

- Vérifier que les avatars (ajoutés lors du correctif précédent) sont bien
  alignés verticalement avec le haut des bulles/cartes de message, sur les
  deux rôles (user et assistant)
- Si le contraste texte-blanc-sur-`--accent` des bulles utilisateur est
  jugé insuffisant à l'œil une fois la landing/le badge en place, foncer
  légèrement `--accent` pour ce contexte uniquement (pas un changement de
  token global — décision visuelle à l'implémentation, pas de valeur
  imposée ici)

## Tests

Pas de suite de tests automatisés frontend dans ce chantier (cohérent avec
la décision actée au chantier précédent). Vérification manuelle documentée
dans le plan : navigation `/` → landing affichée sans être connecté,
bouton « Se connecter » mène à `/login`, badge de certitude affiché avec la
bonne couleur pour au moins un cas de chaque niveau (peut nécessiter de
forcer artificiellement le Markdown de test si le LLM ne varie pas les 3
niveaux facilement), bouton copier fonctionnel (contenu presse-papiers
vérifié), input reste visible en scrollant une longue conversation.
