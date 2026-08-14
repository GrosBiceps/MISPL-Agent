# Chantier B — Historique de sessions de chat en sidebar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persister les conversations de chat côté serveur (rattachées au compte) et exposer une sidebar repliable pour naviguer dans l'historique, remplaçant l'état React volatile actuel.

**Architecture:** Deux nouveaux modèles SQLAlchemy (`Conversation`, `Message`), un routeur FastAPI CRUD minimal (`/conversations`), une extension de `POST /chat/ask` pour persister chaque tour, et côté frontend une sidebar Next.js groupant les conversations par catégorie temporelle.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (style `Mapped`/`mapped_column`), pytest, Next.js 16 (App Router, TypeScript, CSS pur — pas de Tailwind).

## Global Constraints

- Nouveaux modèles SQLAlchemy : suivre le style `Mapped`/`mapped_column` déjà utilisé dans `api/models.py` (voir `User`/`UserSession`).
- Toute tentative d'accès à une conversation n'appartenant pas à l'utilisateur courant répond **404** (jamais 403), cohérent avec le reste de l'API.
- Titre de conversation = 50 premiers caractères de la première question de l'utilisateur, tronqués et suffixés de « … » si dépassement ; jamais modifiable dans ce chantier (pas de renommage en scope).
- Aucun message n'est persisté quand la requête est bloquée par le DLP (`dlp_check` retourne `blocked=True`).
- Aucune purge automatique / politique de rétention — la table `conversations` (et `messages`) croît sans limite, décision déjà actée lors de la revue finale du chantier auth pour la table `sessions`.
- Le mécanisme `conversation_history` existant (reconstruit côté client à chaque requête, envoyé à `ask_mispl()`) n'est **pas** modifié — la persistance serveur ajoutée ici est un enregistrement parallèle, pas un remplacement.
- Frontend : **aucun framework de test n'est configuré dans ce projet** (pas de Jest/Vitest, pas de script `"test"` dans `frontend/package.json`, aucun fichier `*.test.ts*` existant). Ne pas en introduire pour ce chantier. Vérification des tâches frontend via `npx tsc --noEmit` (depuis `frontend/`) et `npm run build`, plus les étapes de vérification manuelle décrites dans chaque tâche.
- Réutiliser tel quel les tokens CSS « Quiet Luxury » déjà définis dans `frontend/app/globals.css` (`--bg`, `--surface`, `--ink`, `--ink-soft`, `--line`, `--accent`, `--accent-soft`, `--danger`, `--radius`, `--serif`, `--sans`) — ne créer aucune nouvelle couleur.
- Sidebar : largeur fixe 260px dépliée, repliable via bouton toggle, état persisté en `localStorage` sous la clé `sidebar-collapsed`.
- Ne pas utiliser `var(--danger)` comme couleur de texte directe (pattern déjà établi dans `.error-banner` : bordure/fond en `--danger`, texte en `--ink`) — évite de reproduire un problème de contraste déjà corrigé ailleurs dans ce projet.

## File Structure

**Backend :**
- Modifier `api/models.py` — ajoute `Conversation`, `Message`.
- Modifier `api/schemas.py` — ajoute `ConversationSummaryOut`, `MessageOut`, `ConversationDetailOut` ; étend `ChatRequest`/`ChatResponse` avec `conversation_id`.
- Créer `api/routers/conversations.py` — CRUD `GET /conversations`, `GET /conversations/{id}`, `DELETE /conversations/{id}`.
- Modifier `api/routers/chat.py` — persiste la conversation/les messages après chaque tour réussi.
- Modifier `api/main.py` — enregistre le nouveau routeur.
- Modifier `tests/api/test_models.py` — tests des nouveaux modèles.
- Créer `tests/api/test_conversation_routes.py` — tests du CRUD.
- Modifier `tests/api/test_chat_routes.py` — tests de la persistance dans `/chat/ask`.

**Frontend :**
- Modifier `frontend/lib/api.ts` — types + fonctions `listConversations`, `getConversation`, `deleteConversation` ; étend `askChat`/`ChatResponse`.
- Créer `frontend/lib/conversationGroups.ts` — regroupement temporel pur (Aujourd'hui / Hier / 7 derniers jours / Plus ancien).
- Créer `frontend/components/ConversationSidebar.tsx` — composant sidebar.
- Modifier `frontend/app/chat/page.tsx` — layout deux colonnes, câblage sidebar ↔ état du chat.
- Modifier `frontend/app/globals.css` — styles sidebar.

---

### Task 1: Modèles `Conversation` et `Message`

**Files:**
- Modify: `api/models.py`
- Test: `tests/api/test_models.py`

**Interfaces:**
- Produces : `Conversation(id, user_id, title, created_at, updated_at, messages)` et `Message(id, conversation_id, role, content, sources_json, created_at, conversation)`, importables via `from api.models import Conversation, Message`. `Conversation.messages` est triée par `Message.id` et se supprime en cascade (`cascade="all, delete-orphan"`).

- [ ] **Step 1: Écrire les tests des nouveaux modèles**

Ajouter à la fin de `tests/api/test_models.py` (après `TestUserSessionModel`), et ajouter `Conversation, Message` à l'import existant en haut du fichier (`from api.models import Conversation, Message, User, UserSession`) :

```python
class TestConversationModel:
    def test_create_conversation_linked_to_user(self):
        db = make_session()
        user = User(email="tech3@labo.fr", password_hash="h", display_name="Tech Trois", platform_role="user")
        db.add(user)
        db.commit()

        conv = Conversation(user_id=user.id, title="Comment utiliser Substr ?")
        db.add(conv)
        db.commit()

        fetched = db.query(Conversation).filter(Conversation.user_id == user.id).one()
        assert fetched.title == "Comment utiliser Substr ?"
        assert fetched.messages == []


class TestMessageModel:
    def test_create_messages_linked_to_conversation(self):
        db = make_session()
        user = User(email="tech4@labo.fr", password_hash="h", display_name="Tech Quatre", platform_role="user")
        db.add(user)
        db.commit()

        conv = Conversation(user_id=user.id, title="Formater une date")
        db.add(conv)
        db.commit()

        db.add(Message(conversation_id=conv.id, role="user", content="Comment formater la date ?"))
        db.add(
            Message(
                conversation_id=conv.id,
                role="assistant",
                content="Utilisez FormatDate()",
                sources_json='[{"function_name": "FormatDate"}]',
            )
        )
        db.commit()

        fetched = db.get(Conversation, conv.id)
        assert len(fetched.messages) == 2
        assert fetched.messages[0].role == "user"
        assert fetched.messages[1].sources_json == '[{"function_name": "FormatDate"}]'

    def test_deleting_conversation_cascades_to_messages(self):
        db = make_session()
        user = User(email="tech5@labo.fr", password_hash="h", display_name="Tech Cinq", platform_role="user")
        db.add(user)
        db.commit()

        conv = Conversation(user_id=user.id, title="Test cascade")
        db.add(conv)
        db.commit()
        db.add(Message(conversation_id=conv.id, role="user", content="Question"))
        db.commit()
        conv_id = conv.id

        db.delete(conv)
        db.commit()

        assert db.query(Message).filter(Message.conversation_id == conv_id).count() == 0
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_models.py -v`
Expected: FAIL (`ImportError: cannot import name 'Conversation'`)

- [ ] **Step 3: Ajouter les modèles à `api/models.py`**

Ajouter à la fin du fichier `api/models.py` (après la classe `UserSession`) :

```python


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    sources_json: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_models.py -v`
Expected: PASS (tous les tests, y compris ceux préexistants sur `User`/`UserSession`)

- [ ] **Step 5: Commit**

```bash
git add api/models.py tests/api/test_models.py
git commit -m "feat(api): modèles Conversation et Message pour l'historique de chat"
```

---

### Task 2: Schémas et routeur `/conversations`

**Files:**
- Modify: `api/schemas.py`
- Create: `api/routers/conversations.py`
- Modify: `api/main.py`
- Test: `tests/api/test_conversation_routes.py`

**Interfaces:**
- Consumes : `Conversation`, `Message` (Task 1) ; `get_current_user` de `api/dependencies.py` ; `get_db` de `api/db.py` ; `SourceOut` (déjà défini dans `api/schemas.py`).
- Produces : schémas `ConversationSummaryOut(id, title, updated_at)`, `MessageOut(role, content, sources, created_at)`, `ConversationDetailOut(id, title, messages)`, importables via `from api.schemas import ConversationSummaryOut, MessageOut, ConversationDetailOut`. Routeur `conversations.router` (préfixe `/conversations`), importable via `from api.routers import conversations` — consommé par Task 4 (le routeur chat n'a pas besoin de ce module, mais partage le même pattern d'ownership check).

- [ ] **Step 1: Écrire les tests du CRUD conversations**

Créer `tests/api/test_conversation_routes.py` :

```python
"""Tests des routes /conversations — isolation par compte, CRUD historique de chat."""

from api.models import Conversation, Message, User
from api.security import hash_password


def make_user(db_session_factory, **overrides):
    defaults = dict(
        email="tech@labo.fr", password_hash=hash_password("MotDePasseRobuste1!"),
        display_name="Tech", platform_role="user", can_use_dsi_mode=False, is_active=True,
    )
    defaults.update(overrides)
    db = db_session_factory()
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.close()


def login(client, email="tech@labo.fr", password="MotDePasseRobuste1!"):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


def make_conversation(db_session_factory, user_email, title="Titre test"):
    db = db_session_factory()
    user = db.query(User).filter(User.email == user_email).one()
    conv = Conversation(user_id=user.id, title=title)
    db.add(conv)
    db.commit()
    conv_id = conv.id
    db.close()
    return conv_id


class TestAuthRequired:
    def test_list_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.get("/conversations")
        assert resp.status_code == 401

    def test_get_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.get("/conversations/1")
        assert resp.status_code == 401

    def test_delete_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.delete("/conversations/1")
        assert resp.status_code == 401


class TestListConversations:
    def test_empty_list_for_new_user(self, client, db_session_factory):
        make_user(db_session_factory)
        login(client)
        resp = client.get("/conversations")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_only_returns_own_conversations(self, client, db_session_factory):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")
        make_conversation(db_session_factory, "a@labo.fr", title="Conversation de A")
        make_conversation(db_session_factory, "b@labo.fr", title="Conversation de B")

        login(client, email="a@labo.fr")
        resp = client.get("/conversations")
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert titles == ["Conversation de A"]


class TestGetConversation:
    def test_returns_messages_in_order(self, client, db_session_factory):
        make_user(db_session_factory)
        conv_id = make_conversation(db_session_factory, "tech@labo.fr", title="Ma conversation")

        db = db_session_factory()
        db.add(Message(conversation_id=conv_id, role="user", content="Question ?"))
        db.add(
            Message(
                conversation_id=conv_id,
                role="assistant",
                content="Réponse.",
                sources_json='[{"function_name": "Substr", "source": "doc.md", "score": 0.9, "exact_match": true}]',
            )
        )
        db.commit()

        login(client)
        resp = client.get(f"/conversations/{conv_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Ma conversation"
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][1]["sources"][0]["function_name"] == "Substr"

    def test_returns_404_for_other_users_conversation(self, client, db_session_factory):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")
        conv_id = make_conversation(db_session_factory, "a@labo.fr")

        login(client, email="b@labo.fr")
        resp = client.get(f"/conversations/{conv_id}")
        assert resp.status_code == 404

    def test_returns_404_for_nonexistent_conversation(self, client, db_session_factory):
        make_user(db_session_factory)
        login(client)
        resp = client.get("/conversations/999")
        assert resp.status_code == 404


class TestDeleteConversation:
    def test_deletes_own_conversation_and_messages(self, client, db_session_factory):
        make_user(db_session_factory)
        conv_id = make_conversation(db_session_factory, "tech@labo.fr")

        db = db_session_factory()
        db.add(Message(conversation_id=conv_id, role="user", content="Question ?"))
        db.commit()

        login(client)
        resp = client.delete(f"/conversations/{conv_id}")
        assert resp.status_code == 200

        db = db_session_factory()
        assert db.get(Conversation, conv_id) is None
        assert db.query(Message).filter(Message.conversation_id == conv_id).count() == 0

    def test_returns_404_for_other_users_conversation(self, client, db_session_factory):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")
        conv_id = make_conversation(db_session_factory, "a@labo.fr")

        login(client, email="b@labo.fr")
        resp = client.delete(f"/conversations/{conv_id}")
        assert resp.status_code == 404

        db = db_session_factory()
        assert db.get(Conversation, conv_id) is not None
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_conversation_routes.py -v`
Expected: FAIL (404 devient 404 générique FastAPI "Not Found" pour route inexistante au lieu de la réponse attendue, ou erreur de connexion — la route `/conversations` n'existe pas encore)

- [ ] **Step 3: Ajouter les schémas dans `api/schemas.py`**

Ajouter `import datetime` en haut du fichier (juste après `from typing import Literal`) :

```python
import datetime
from typing import Literal
```

Ajouter à la fin du fichier `api/schemas.py` :

```python


class ConversationSummaryOut(BaseModel):
    id: int
    title: str
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceOut] | None = None
    created_at: datetime.datetime


class ConversationDetailOut(BaseModel):
    id: int
    title: str
    messages: list[MessageOut]
```

- [ ] **Step 4: Étendre `ChatRequest`/`ChatResponse` pour `conversation_id`**

Dans `api/schemas.py`, modifier la classe `ChatRequest` :

```python
class ChatRequest(BaseModel):
    question: str
    lab_context: str | None = None
    conversation_history: list[ChatHistoryMessage] | None = None
    conversation_id: int | None = None
```

Et la classe `ChatResponse` :

```python
class ChatResponse(BaseModel):
    response: str | None
    sources: list[SourceOut]
    blocked: bool
    dlp_alerts: list[str]
    conversation_id: int | None = None
```

- [ ] **Step 5: Créer le routeur `api/routers/conversations.py`**

```python
"""Routes de gestion des conversations persistées — historique de chat par compte."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import get_current_user
from api.models import Conversation, User
from api.schemas import ConversationDetailOut, ConversationSummaryOut, MessageOut, SourceOut

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _get_owned_conversation_or_404(db: DBSession, conversation_id: int, user_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return conversation


@router.get("", response_model=list[ConversationSummaryOut])
def list_conversations(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)
):
    conversation = _get_owned_conversation_or_404(db, conversation_id, user.id)
    messages = [
        MessageOut(
            role=m.role,
            content=m.content,
            sources=[SourceOut(**s) for s in json.loads(m.sources_json)] if m.sources_json else None,
            created_at=m.created_at,
        )
        for m in conversation.messages
    ]
    return ConversationDetailOut(id=conversation.id, title=conversation.title, messages=messages)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)
):
    conversation = _get_owned_conversation_or_404(db, conversation_id, user.id)
    db.delete(conversation)
    db.commit()
    return {"detail": "Conversation supprimée"}
```

- [ ] **Step 6: Enregistrer le routeur dans `api/main.py`**

Modifier la ligne d'import :

```python
from api.routers import admin, auth, chat, conversations
```

Et ajouter après `app.include_router(chat.router)` :

```python
app.include_router(conversations.router)
```

- [ ] **Step 7: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_conversation_routes.py -v`
Expected: PASS (tous les tests)

- [ ] **Step 8: Lancer toute la suite backend pour vérifier l'absence de régression**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/ tests/security/ -v`
Expected: PASS (tous les tests existants restent verts)

- [ ] **Step 9: Commit**

```bash
git add api/schemas.py api/routers/conversations.py api/main.py tests/api/test_conversation_routes.py
git commit -m "feat(api): CRUD /conversations (liste, détail, suppression)"
```

---

### Task 3: Persistance dans `POST /chat/ask`

**Files:**
- Modify: `api/routers/chat.py`
- Test: `tests/api/test_chat_routes.py`

**Interfaces:**
- Consumes : `Conversation`, `Message` (Task 1) ; `ChatRequest.conversation_id`, `ChatResponse.conversation_id` (Task 2).
- Produces : `ChatResponse.conversation_id` toujours renseigné après un tour réussi (jamais `None` sauf si `blocked=True`) — consommé par le frontend en Task 4.

- [ ] **Step 1: Écrire les tests de persistance**

Ajouter en haut de `tests/api/test_chat_routes.py`, à l'import existant :

```python
from api.models import Conversation, Message, User
```

(remplace la ligne `from api.models import User` existante)

Ajouter à la fin du fichier `tests/api/test_chat_routes.py` :

```python


class TestConversationPersistence:
    def test_creates_new_conversation_when_none_provided(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", lambda question, **kwargs: ("Voici la réponse", []))

        resp = client.post("/chat/ask", json={"question": "Comment utiliser Substr ?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["conversation_id"] is not None

        db = db_session_factory()
        conv = db.get(Conversation, body["conversation_id"])
        assert conv is not None
        assert conv.title == "Comment utiliser Substr ?"
        messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.id).all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Comment utiliser Substr ?"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Voici la réponse"

    def test_reuses_provided_conversation_id(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", lambda question, **kwargs: ("réponse 1", []))
        first = client.post("/chat/ask", json={"question": "Question initiale ?"})
        conversation_id = first.json()["conversation_id"]

        monkeypatch.setattr(chat_router, "ask_mispl", lambda question, **kwargs: ("réponse 2", []))
        second = client.post(
            "/chat/ask",
            json={"question": "Question suivante ?", "conversation_id": conversation_id},
        )
        assert second.status_code == 200
        assert second.json()["conversation_id"] == conversation_id

        db = db_session_factory()
        messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.id).all()
        assert len(messages) == 4

    def test_conversation_id_owned_by_other_user_returns_404(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory, email="a@labo.fr")
        make_user(db_session_factory, email="b@labo.fr")

        db = db_session_factory()
        owner = db.query(User).filter(User.email == "a@labo.fr").one()
        other_conv = Conversation(user_id=owner.id, title="Conversation de A")
        db.add(other_conv)
        db.commit()
        other_conv_id = other_conv.id

        login(client, email="b@labo.fr")
        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", lambda question, **kwargs: ("ok", []))

        resp = client.post(
            "/chat/ask",
            json={"question": "Question ?", "conversation_id": other_conv_id},
        )
        assert resp.status_code == 404

    def test_blocked_dlp_message_does_not_create_conversation(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (True, ["IPP/NIP patient"]))
        monkeypatch.setattr(chat_router, "ask_mispl", lambda *a, **kw: ("ne doit jamais arriver", []))

        resp = client.post("/chat/ask", json={"question": "IPP:1234567 quoi faire ?"})
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] is None

        db = db_session_factory()
        assert db.query(Conversation).count() == 0
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_chat_routes.py -v -k TestConversationPersistence`
Expected: FAIL (`conversation_id` absent de la réponse, ou `KeyError`)

- [ ] **Step 3: Modifier `api/routers/chat.py`**

Remplacer tout le contenu du fichier par :

```python
"""Route de chat — encapsule ask_mispl() derrière l'authentification de compte."""

from __future__ import annotations

import datetime
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import get_current_user
from api.models import Conversation, Message, User
from api.schemas import ChatRequest, ChatResponse, SourceOut
from src.agent.mispl_agent import ask_mispl
from src.security.access_mode import access_mode_for_user
from src.security.dlp import dlp_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

TITLE_MAX_LENGTH = 50


def _get_owned_conversation_or_404(db: DBSession, conversation_id: int, user_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return conversation


def _make_title(question: str) -> str:
    stripped = question.strip()
    if len(stripped) <= TITLE_MAX_LENGTH:
        return stripped
    return stripped[:TITLE_MAX_LENGTH].rstrip() + "…"


@router.post("/ask", response_model=ChatResponse)
def ask(payload: ChatRequest, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = None
    if payload.conversation_id is not None:
        conversation = _get_owned_conversation_or_404(db, payload.conversation_id, user.id)

    question_enriched = payload.question
    if payload.lab_context:
        question_enriched = f"[Contexte labo: {payload.lab_context.strip()}]\n\n{payload.question}"

    history_text = "\n".join(m.content for m in (payload.conversation_history or []))
    blocked, dlp_alerts = dlp_check(f"{question_enriched}\n{history_text}" if history_text else question_enriched)
    if blocked:
        logger.warning(f"[DLP] Message bloqué — patterns: {dlp_alerts}")
        return ChatResponse(response=None, sources=[], blocked=True, dlp_alerts=dlp_alerts, conversation_id=None)

    access_mode = access_mode_for_user(user.can_use_dsi_mode)

    history = (
        [{"role": m.role, "content": m.content} for m in payload.conversation_history]
        if payload.conversation_history
        else None
    )

    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
            conversation_history=history,
        )
    except Exception:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"[{error_id}] Erreur ask_mispl", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service temporairement indisponible — réessayez dans quelques instants. (Référence : {error_id})",
        )

    sources = [
        SourceOut(
            function_name=d.get("function_name", ""),
            source=d.get("source", ""),
            score=round(d.get("score", 0), 3),
            exact_match=d.get("exact_match", False),
        )
        for d in docs
    ]

    if conversation is None:
        conversation = Conversation(user_id=user.id, title=_make_title(payload.question))
        db.add(conversation)
        db.flush()

    now = datetime.datetime.utcnow()
    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question, created_at=now))
    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text or "",
            sources_json=json.dumps([s.model_dump() for s in sources]) if sources else None,
            created_at=now,
        )
    )
    conversation.updated_at = now
    db.commit()

    return ChatResponse(
        response=response_text,
        sources=sources,
        blocked=False,
        dlp_alerts=dlp_alerts,
        conversation_id=conversation.id,
    )
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_chat_routes.py -v`
Expected: PASS (tous les tests, y compris ceux préexistants sur DLP/auth/access_mode)

- [ ] **Step 5: Lancer toute la suite backend pour vérifier l'absence de régression**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/ tests/security/ -v`
Expected: PASS (tous les tests existants restent verts)

- [ ] **Step 6: Commit**

```bash
git add api/routers/chat.py tests/api/test_chat_routes.py
git commit -m "feat(api): persiste conversation et messages dans POST /chat/ask"
```

---

### Task 4: Client API frontend

**Files:**
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Consumes : `ConversationSummaryOut`, `MessageOut`, `ConversationDetailOut`, `ChatResponse.conversation_id`, `ChatRequest.conversation_id` (Task 2/3, via le contrat JSON de l'API).
- Produces : `ConversationSummary { id, title, updated_at }`, `ConversationMessage { role, content, sources, created_at }`, `ConversationDetail { id, title, messages }`, fonctions `listConversations()`, `getConversation(id)`, `deleteConversation(id)`, et `askChat(question, labContext?, conversationHistory?, conversationId?)` — consommés par Task 5 et Task 6.

- [ ] **Step 1: Ajouter les types et fonctions dans `frontend/lib/api.ts`**

Modifier l'interface `ChatResponse` existante :

```typescript
export interface ChatResponse {
  response: string | null;
  sources: SourceOut[];
  blocked: boolean;
  dlp_alerts: string[];
  conversation_id: number | null;
}
```

Modifier la signature de `askChat` :

```typescript
export function askChat(
  question: string,
  labContext?: string,
  conversationHistory?: ChatHistoryMessage[],
  conversationId?: number | null
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      lab_context: labContext || undefined,
      conversation_history: conversationHistory && conversationHistory.length > 0 ? conversationHistory : undefined,
      conversation_id: conversationId ?? undefined,
    }),
  });
}
```

Ajouter à la fin du fichier `frontend/lib/api.ts` :

```typescript

export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
  sources: SourceOut[] | null;
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  title: string;
  messages: ConversationMessage[];
}

export function listConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>("/conversations");
}

export function getConversation(id: number): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${id}`);
}

export function deleteConversation(id: number): Promise<{ detail: string }> {
  return request<{ detail: string }>(`/conversations/${id}`, { method: "DELETE" });
}
```

- [ ] **Step 2: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur (le fichier n'est encore consommé par aucun composant, donc aucun appelant à `askChat` n'est cassé par le nouveau paramètre optionnel `conversationId`)

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(frontend): client API pour l'historique de conversations"
```

---

### Task 5: Regroupement temporel et composant sidebar

**Files:**
- Create: `frontend/lib/conversationGroups.ts`
- Create: `frontend/components/ConversationSidebar.tsx`

**Interfaces:**
- Consumes : `ConversationSummary` (Task 4).
- Produces : `groupConversationsByDate(conversations, now?) -> ConversationGroup[]` où `ConversationGroup = { label: string, conversations: ConversationSummary[] }`, exporté via `from "../lib/conversationGroups"` — consommé par `ConversationSidebar`. Composant `ConversationSidebar` avec les props `{ conversations, activeId, collapsed, error, userDisplayName, onToggleCollapse, onNew, onSelect, onDelete }`, exporté par défaut depuis `frontend/components/ConversationSidebar.tsx` — consommé par Task 6.

- [ ] **Step 1: Créer `frontend/lib/conversationGroups.ts`**

```typescript
import { ConversationSummary } from "./api";

export interface ConversationGroup {
  label: string;
  conversations: ConversationSummary[];
}

const GROUP_LABELS = ["Aujourd'hui", "Hier", "7 derniers jours", "Plus ancien"] as const;

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function groupConversationsByDate(
  conversations: ConversationSummary[],
  now: Date = new Date()
): ConversationGroup[] {
  const today = startOfDay(now);
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  const buckets: Record<(typeof GROUP_LABELS)[number], ConversationSummary[]> = {
    "Aujourd'hui": [],
    Hier: [],
    "7 derniers jours": [],
    "Plus ancien": [],
  };

  for (const conv of conversations) {
    const updated = new Date(conv.updated_at);
    if (updated >= today) {
      buckets["Aujourd'hui"].push(conv);
    } else if (updated >= yesterday) {
      buckets.Hier.push(conv);
    } else if (updated >= weekAgo) {
      buckets["7 derniers jours"].push(conv);
    } else {
      buckets["Plus ancien"].push(conv);
    }
  }

  return GROUP_LABELS.map((label) => ({ label, conversations: buckets[label] })).filter(
    (g) => g.conversations.length > 0
  );
}
```

- [ ] **Step 2: Vérification manuelle de la logique de regroupement**

Pas de test automatisé possible (aucun framework de test frontend dans ce projet — voir Global Constraints). Vérifier la logique par lecture attentive du code ci-dessus contre ces trois cas, et confirmer qu'ils sont couverts par construction :
- une conversation avec `updated_at` = aujourd'hui à 00h01 → doit tomber dans `"Aujourd'hui"` (comparaison `>= today` où `today` est minuit du jour courant) ;
- une conversation avec `updated_at` = hier 23h59 → doit tomber dans `"Hier"` (comparaison `>= yesterday` et `< today`, capturée par l'ordre des `if/else if`) ;
- une conversation avec `updated_at` = il y a 10 jours → doit tomber dans `"Plus ancien"` (aucune des trois premières conditions ne matche).

La vérification définitive se fera dans le navigateur à l'étape manuelle de Task 6 (Step 5).

- [ ] **Step 3: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 4: Créer `frontend/components/ConversationSidebar.tsx`**

```tsx
"use client";

import { ConversationSummary } from "../lib/api";
import { groupConversationsByDate } from "../lib/conversationGroups";

interface Props {
  conversations: ConversationSummary[];
  activeId: number | null;
  collapsed: boolean;
  error: string | null;
  userDisplayName: string;
  onToggleCollapse: () => void;
  onNew: () => void;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  collapsed,
  error,
  userDisplayName,
  onToggleCollapse,
  onNew,
  onSelect,
  onDelete,
}: Props) {
  if (collapsed) {
    return (
      <aside className="conv-sidebar conv-sidebar-collapsed">
        <button
          className="ghost conv-sidebar-toggle"
          onClick={onToggleCollapse}
          aria-label="Afficher l'historique"
        >
          »
        </button>
      </aside>
    );
  }

  const groups = groupConversationsByDate(conversations);

  return (
    <aside className="conv-sidebar">
      <div className="conv-sidebar-header">
        <span className="conv-sidebar-logo">MISPL Agent</span>
        <button
          className="ghost conv-sidebar-toggle"
          onClick={onToggleCollapse}
          aria-label="Masquer l'historique"
        >
          «
        </button>
      </div>
      <button className="conv-sidebar-new-btn" onClick={onNew}>
        + Nouvelle conversation
      </button>
      {error && <div className="conv-sidebar-error">{error}</div>}
      <div className="conv-sidebar-list">
        {conversations.length === 0 && !error && (
          <p className="conv-sidebar-empty">Aucune conversation pour l&apos;instant</p>
        )}
        {groups.map((group) => (
          <div key={group.label} className="conv-sidebar-group">
            <div className="conv-sidebar-group-label">{group.label}</div>
            {group.conversations.map((conv) => (
              <div
                key={conv.id}
                className={`conv-sidebar-item${conv.id === activeId ? " active" : ""}`}
                onClick={() => onSelect(conv.id)}
              >
                <span className="conv-sidebar-item-title">{conv.title}</span>
                <button
                  className="conv-sidebar-item-delete"
                  aria-label="Supprimer la conversation"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("Supprimer cette conversation ?")) {
                      onDelete(conv.id);
                    }
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="conv-sidebar-footer">{userDisplayName}</div>
    </aside>
  );
}
```

- [ ] **Step 5: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/conversationGroups.ts frontend/components/ConversationSidebar.tsx
git commit -m "feat(frontend): regroupement temporel et composant sidebar de conversations"
```

---

### Task 6: Intégration dans la page de chat + styles

**Files:**
- Modify: `frontend/app/chat/page.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes : `ConversationSidebar` (Task 5), `listConversations`, `getConversation`, `deleteConversation`, `askChat` avec `conversationId`, `ConversationSummary` (Task 4).

- [ ] **Step 1: Ajouter les styles sidebar dans `frontend/app/globals.css`**

Ajouter à la fin du fichier `frontend/app/globals.css` :

```css

.app-layout {
  display: flex;
  min-height: 100vh;
}

.chat-main {
  flex: 1;
  min-width: 0;
}

.conv-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border-right: 1px solid var(--line);
  padding: 16px 12px;
}
.conv-sidebar-collapsed {
  width: 44px;
  align-items: center;
  padding: 16px 6px;
}
.conv-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.conv-sidebar-logo {
  font-family: var(--serif);
  font-weight: 600;
  font-size: 15px;
}
.conv-sidebar-toggle {
  padding: 4px 8px;
  font-size: 13px;
  border-radius: 8px;
}
.conv-sidebar-new-btn {
  width: 100%;
  text-align: left;
  margin-bottom: 14px;
  font-size: 13px;
  padding: 9px 12px;
}
.conv-sidebar-list {
  flex: 1;
  overflow-y: auto;
}
.conv-sidebar-group {
  margin-bottom: 14px;
}
.conv-sidebar-group-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-soft);
  padding: 4px 8px;
}
.conv-sidebar-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 8px 8px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
.conv-sidebar-item:hover {
  background: var(--accent-soft);
}
.conv-sidebar-item.active {
  background: var(--accent-soft);
  font-weight: 600;
}
.conv-sidebar-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.conv-sidebar-item-delete {
  background: transparent;
  border: none;
  color: var(--ink-soft);
  font-size: 14px;
  padding: 0 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.conv-sidebar-item:hover .conv-sidebar-item-delete {
  opacity: 1;
}
.conv-sidebar-item-delete:hover {
  color: var(--danger);
}
.conv-sidebar-empty {
  font-size: 12.5px;
  color: var(--ink-soft);
  padding: 8px;
}
.conv-sidebar-error {
  border-left: 3px solid var(--danger);
  background: #f6ece9;
  color: var(--ink);
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 8px;
}
.conv-sidebar-footer {
  border-top: 1px solid var(--line);
  padding-top: 12px;
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--ink-soft);
}
```

- [ ] **Step 2: Réécrire `frontend/app/chat/page.tsx`**

Remplacer tout le contenu du fichier par :

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  askChat,
  getMe,
  logout,
  listConversations,
  getConversation,
  deleteConversation,
  ApiError,
  MeResponse,
  SourceOut,
  ConversationSummary,
} from "../../lib/api";
import { getInitials } from "../../lib/avatar";
import ChatMessage from "../../components/ChatMessage";
import EmptyState from "../../components/EmptyState";
import ThinkingIndicator from "../../components/ThinkingIndicator";
import BetaBadge from "../../components/BetaBadge";
import ConversationSidebar from "../../components/ConversationSidebar";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
  warning?: string[];
}

const EXAMPLES = [
  "Comment utiliser Substr pour extraire une sous-chaine ?",
  "Comment formater la date du jour en MISPL ?",
  "Comment écrire un log d'audit avec AddLogEntry ?",
  "Comment récupérer l'utilisateur connecté ?",
];

const SIDEBAR_COLLAPSED_KEY = "sidebar-collapsed";

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [labContext, setLabContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarError, setSidebarError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  useEffect(() => {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    if (stored === "true") setSidebarCollapsed(true);
  }, []);

  useEffect(() => {
    if (user) refreshConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshConversations() {
    try {
      const list = await listConversations();
      setConversations(list);
      setSidebarError(null);
    } catch {
      setSidebarError("Impossible de charger l'historique");
    }
  }

  function toggleSidebar() {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      return next;
    });
  }

  async function handleAsk(q: string) {
    if (!q.trim() || loading) return;
    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const result = await askChat(q, labContext || undefined, history, activeConversationId);
      if (result.blocked) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `🚫 Message bloqué — données sensibles détectées (${result.dlp_alerts.join(", ")}). Ne pas inclure de données patient (IPP, NIR...) dans les questions ou le contexte labo.`,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.response ?? "",
            sources: result.sources,
            warning: result.dlp_alerts.length > 0 ? result.dlp_alerts : undefined,
          },
        ]);
        if (result.conversation_id !== null && result.conversation_id !== activeConversationId) {
          setActiveConversationId(result.conversation_id);
        }
        refreshConversations();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      const content =
        err instanceof ApiError
          ? err.message
          : "Impossible de contacter le serveur — vérifiez votre connexion ou réessayez dans quelques instants.";
      setMessages((prev) => [...prev, { role: "assistant", content }]);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setMessages([]);
    setActiveConversationId(null);
  }

  async function handleSelectConversation(id: number) {
    if (id === activeConversationId) return;
    try {
      const detail = await getConversation(id);
      setMessages(
        detail.messages.map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sources ?? undefined,
        }))
      );
      setActiveConversationId(id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      setSidebarError("Impossible de charger cette conversation");
    }
  }

  async function handleDeleteConversation(id: number) {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === activeConversationId) {
        handleReset();
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login?expired=1");
        return;
      }
      setSidebarError("Impossible de supprimer cette conversation");
    }
  }

  async function handleLogout() {
    await logout().catch(() => {});
    router.push("/login");
  }

  if (!user) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  return (
    <div className="app-layout">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        collapsed={sidebarCollapsed}
        error={sidebarError}
        userDisplayName={user.display_name}
        onToggleCollapse={toggleSidebar}
        onNew={handleReset}
        onSelect={handleSelectConversation}
        onDelete={handleDeleteConversation}
      />
      <main className="chat-main" style={{ maxWidth: 780, margin: "0 auto", padding: "2rem 1.5rem 1rem" }}>
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

        {messages.length === 0 && !loading ? (
          <EmptyState examples={EXAMPLES} onPick={handleAsk} />
        ) : (
          <div>
            {messages.map((m, i) => (
              <ChatMessage
                key={i}
                role={m.role}
                content={m.content}
                sources={m.sources}
                warning={m.warning}
                userInitials={getInitials(user.display_name)}
              />
            ))}
            {loading && <ThinkingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}

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
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 4: Vérifier le build de production**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur (avertissements de lint désactivés — pas d'ESLint configuré dans ce projet)

- [ ] **Step 5: Vérification manuelle dans le navigateur**

Avec le backend (`uvicorn api.main:app --port 8000`, `.venv` activé) et le frontend (`npm run dev`, port 3000) lancés :

1. Se connecter avec un compte existant → la sidebar apparaît à gauche, vide (« Aucune conversation pour l'instant »), logo « MISPL Agent » en haut, nom du compte en bas.
2. Poser une question → après la réponse, une nouvelle entrée apparaît dans la sidebar sous « Aujourd'hui » avec un titre tronqué à 50 caractères.
3. Poser une deuxième question dans la même session → toujours une seule entrée dans la sidebar (pas de doublon), la conversation grandit.
4. Cliquer sur « + Nouvelle conversation » → le chat se vide, la sidebar garde l'ancienne entrée.
5. Cliquer sur l'ancienne entrée dans la sidebar → les messages précédents se rechargent à l'identique (y compris les sources).
6. Survoler une entrée de la sidebar → un bouton « × » apparaît ; cliquer dessus → confirmation navigateur → suppression → l'entrée disparaît de la sidebar.
7. Supprimer la conversation actuellement affichée → le chat revient à l'état vide.
8. Cliquer sur le bouton toggle (« « ») → la sidebar se réduit à une bande étroite avec juste un bouton « » » ; rafraîchir la page (F5) → la sidebar reste repliée (persistance `localStorage`).
9. Se déconnecter puis se reconnecter avec un **autre** compte → la sidebar de ce compte ne montre aucune conversation du premier compte.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/chat/page.tsx frontend/app/globals.css
git commit -m "feat(frontend): intègre la sidebar d'historique dans la page de chat"
```
