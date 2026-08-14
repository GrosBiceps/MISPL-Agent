# Chantier B — Historique de sessions de chat en sidebar — Design

## Contexte

Chaque conversation ne vit aujourd'hui qu'en `useState` côté React
(`frontend/app/chat/page.tsx`) — perdue au rafraîchissement de la page,
sans lien avec le compte utilisateur. Le système de comptes (chantier
auth) et le frontend Next.js « Quiet Luxury » (chantier polish-UI) sont
déjà en place et mergés dans `main`.

Ce chantier ajoute une persistance serveur des conversations, rattachée au
compte, et une sidebar de navigation dans l'historique — inspirée du
pattern `.sidenav-hist` / `.hist-item` du repo sibling
`biochimie-biologbook`.

**À ne pas confondre avec l'existant :**
- `outputs/sessions/` (`src/agent/mispl_agent.py::_save_session`) : journal
  technique d'audit par appel LLM, non lié à `user_id`, non structuré en
  conversations. Reste inchangé.
- `conversation_history` envoyé à `POST /chat/ask` : mémoire court-terme
  reconstruite depuis l'état React à chaque requête (12 derniers
  messages), toujours utilisée comme source du prompt. La persistance
  serveur ajoutée ici est un enregistrement parallèle, pas un remplacement
  de ce mécanisme.

**Hors périmètre explicite** : menu de statistiques de consommation de
tokens (aucun tracking d'usage n'existe côté backend — chantier séparé
non cadré) ; pièce jointe fichier/OCR (chantier séparé non cadré).

## Architecture

Nouveau modèle de données `Conversation` / `Message` en base
(SQLAlchemy, même style que `User` / `UserSession` dans `api/models.py`),
rattaché à `user.id`. Le backend expose un CRUD REST minimal
(`/conversations`), et `POST /chat/ask` est étendu pour accepter un
`conversation_id` optionnel et persister automatiquement chaque tour
(message utilisateur + réponse assistant) côté serveur.

Le frontend ajoute une sidebar repliable dans
`frontend/app/chat/page.tsx`, listant les conversations de l'utilisateur
groupées par catégorie temporelle (Aujourd'hui / Hier / 7 derniers jours /
Plus ancien), avec logo en haut et identifiant compte en bas.

## Modèle de données

```
Conversation
  id: int PK
  user_id: int FK -> users.id
  title: str            # 50 premiers caractères de la 1ère question, tronqués
  created_at: datetime
  updated_at: datetime   # mis à jour à chaque nouveau message, sert au tri/catégorisation

Message
  id: int PK
  conversation_id: int FK -> conversations.id
  role: str ("user" | "assistant")
  content: str
  sources_json: str | None   # JSON sérialisé des SourceOut, uniquement pour role="assistant"
  created_at: datetime
```

`Conversation` a `cascade="all, delete-orphan"` sur ses messages (comme
`User` → `sessions`), pour que la suppression d'une conversation efface
ses messages sans étape séparée.

**Politique de rétention** : aucune purge automatique pour ce chantier.
La table croît indéfiniment — décision cohérente avec la limitation déjà
acceptée pour la table `sessions` lors de la revue finale du chantier
auth. Un futur chantier de maintenance/purge pourra traiter les deux
tables ensemble si le volume devient un problème réel.

**Renommage** : hors périmètre pour ce chantier (titre auto-généré,
immuable). Seule la suppression est en scope.

## API

- `GET /conversations` — liste les conversations de l'utilisateur courant
  (`id`, `title`, `updated_at`), triées par `updated_at` desc. Le
  regroupement par catégorie temporelle se fait côté client.
- `GET /conversations/{id}` — retourne les messages d'une conversation.
  Vérifie `conversation.user_id == current_user.id` ; si ce n'est pas le
  cas, répond 404 (jamais 403, pour ne pas révéler l'existence de
  conversations d'autrui — même logique que le reste de l'API auth).
- `DELETE /conversations/{id}` — supprime (même contrôle d'appartenance,
  même règle 404).
- `POST /chat/ask` — `ChatRequest` gagne un champ
  `conversation_id: int | None = None`.
  - Si `None` : après la réponse de `ask_mispl()`, une nouvelle
    `Conversation` est créée (titre = question tronquée à 50 caractères).
    Son `id` est renvoyé dans un nouveau champ
    `ChatResponse.conversation_id: int | None`, que le frontend retient
    pour les tours suivants de la même conversation.
  - Si fourni : vérifie l'appartenance (404 sinon), réutilise la
    conversation existante, met à jour `updated_at`.
  - Dans les deux cas, le message utilisateur et la réponse assistant
    sont persistés en `Message` **uniquement si la requête n'a pas été
    bloquée par le DLP** — un message bloqué n'est jamais écrit en base,
    pour ne pas persister de tentative de fuite de données patient.
  - Le mécanisme `conversation_history` existant (reconstruit côté
    client, envoyé à chaque requête) n'est pas modifié : il reste la
    source du prompt envoyé à `ask_mispl()`.
  - Une conversation créée uniquement par une requête bloquée par le DLP
    n'est jamais écrite en base (cohérent avec la règle ci-dessus) — donc
    "création au premier message" signifie en réalité "au premier message
    qui aboutit à une réponse persistée".

## Frontend

### Sidebar (`frontend/components/ConversationSidebar.tsx`)

- Logo en haut (asset déjà utilisé sur la landing page).
- Bouton « Nouvelle conversation » sous le logo.
- Liste groupée par catégorie temporelle (Aujourd'hui / Hier / 7 derniers
  jours / Plus ancien), calculée côté client depuis `updated_at`. Chaque
  item affiche le titre tronqué + bouton supprimer (icône, visible au
  survol, confirmation légère avant suppression).
- Identifiant compte (`display_name`) en bas, réutilisant le pattern déjà
  présent dans le header actuel du chat.
- Repliable via bouton toggle, état persisté en `localStorage`
  (clé `sidebar-collapsed`).

### `frontend/app/chat/page.tsx`

Restructuré en layout à deux colonnes (sidebar + zone de chat actuelle,
qui garde son `max-width: 780px` centré dans sa colonne). Nouvel état
`activeConversationId: number | null` :

- Chargement d'une conversation existante (clic sidebar) →
  `GET /conversations/{id}`, remplace `messages`, met à jour
  `activeConversationId`.
- « Nouvelle conversation » → vide `messages` et `activeConversationId`
  côté client uniquement, aucun appel réseau (cohérent avec la décision
  « création au premier message »).
- Après un `askChat()` réussi sans `conversation_id` actif → le
  `conversation_id` renvoyé par la réponse est stocké dans
  `activeConversationId`, et la liste de la sidebar est rafraîchie
  (nouvelle entrée en haut de « Aujourd'hui »).
- Suppression de la conversation actuellement affichée → revient à
  l'état « Nouvelle conversation » vide.

### Dégradation gracieuse

Un échec réseau au chargement de la sidebar affiche un état d'erreur
discret dans la sidebar, sans empêcher le chat de fonctionner (le chat ne
dépend pas de la sidebar pour envoyer des messages).

## Tests

**Backend (pytest) :**
- Appartenance croisée entre comptes sur `GET/DELETE /conversations/{id}`
  → 404 (jamais 403).
- Persistance correcte des deux messages (user + assistant) après un tour
  normal via `/chat/ask`.
- Absence de persistance quand le message est bloqué par le DLP.
- `conversation_id` bien renvoyé et réutilisable sur les tours suivants.
- Cascade de suppression : supprimer une conversation supprime ses
  messages.

**Frontend :**
- Regroupement temporel correct (Aujourd'hui / Hier / 7 derniers jours /
  Plus ancien) selon `updated_at`.
- Bascule repliable + persistance de l'état en `localStorage`.
- Chargement d'une conversation depuis la sidebar remplace bien les
  messages affichés.
- Suppression de la conversation active réinitialise l'état du chat.
