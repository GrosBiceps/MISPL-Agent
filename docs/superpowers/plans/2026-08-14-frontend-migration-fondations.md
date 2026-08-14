# Migration frontend — Fondations (chantier A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer l'UI Streamlit de MISPL Agent par un frontend Next.js dédié couvrant la connexion et le chat de base, en s'appuyant sur l'API FastAPI d'authentification déjà en place.

**Architecture:** Deux process séparés — FastAPI (`api/`, :8000) reçoit un nouveau routeur `/chat/ask` qui encapsule `ask_mispl()` derrière l'authentification de compte ; un nouveau projet Next.js (`frontend/`, :3000) consomme cette API via cookie de session (same-site, CORS activé).

**Tech Stack:** Next.js 15 (App Router, TypeScript, CSS pur), FastAPI (existant), SQLAlchemy (existant), pytest.

## Global Constraints

- Pas de streaming — réponse complète d'un coup
- Clé OpenRouter uniquement côté serveur (`.env`) — jamais exposée au frontend
- Mode DSI/Technicien dérivé du compte via `access_mode_for_user(user.can_use_dsi_mode)` (déjà implémenté dans `src/security/access_mode.py`) — pas de mot de passe DSI dans le nouveau frontend
- Sélecteurs de modèle LLM et de mode skill masqués — tout automatique (`skill_profile=None` côté `ask_mispl`)
- Deux process séparés : FastAPI :8000, Next.js :3000
- `http://localhost:3000` et `http://localhost:8000` sont same-site (même domaine `localhost`) — le cookie `session_token` (`SameSite=Strict`) circule sans changement de sa politique ; seul CORS doit être activé côté FastAPI
- Style CSS pur (variables/tokens), palette Quiet Luxury imposée (voir Task 3)
- `app.py`/Streamlit n'est pas supprimé ni modifié dans ce chantier — il continue de tourner en parallèle
- Pas de suite de tests automatisés côté frontend dans ce chantier — vérification manuelle documentée à chaque tâche frontend, plus `npm run build` comme garde-fou automatisé (erreurs TypeScript/build)

---

## Task 1: Route API `/chat/ask`

**Files:**
- Create: `api/routers/chat.py`
- Modify: `api/schemas.py` (ajout en fin de fichier)
- Modify: `api/main.py` (enregistrement du routeur)
- Test: `tests/api/test_chat_routes.py`

**Interfaces:**
- Consumes: `api.dependencies.get_current_user`, `api.models.User`, `src.agent.mispl_agent.ask_mispl(question, access_mode=..., save_session=...) -> tuple[str, list[dict]]`, `src.security.dlp.dlp_check(text) -> tuple[bool, list[str]]`, `src.security.access_mode.access_mode_for_user(bool) -> str`
- Produces: `POST /chat/ask` — body `{question: str, lab_context?: str}` → `ChatResponse {response: str|None, sources: list[SourceOut], blocked: bool, dlp_alerts: list[str]}` (200), ou 401 (non authentifié), ou 503 (erreur LLM)

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_chat_routes.py
"""Tests de la route /chat/ask — auth requise, DLP, dérivation du mode d'accès, erreurs LLM."""

from api.models import User
from api.security import hash_password
import api.routers.chat as chat_router


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


class TestAuthRequired:
    def test_unauthenticated_returns_401(self, client, db_session_factory):
        resp = client.post("/chat/ask", json={"question": "Comment utiliser Substr ?"})
        assert resp.status_code == 401


class TestDLPBlocking:
    def test_dlp_blocked_does_not_call_ask_mispl(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        calls = []
        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (True, ["IPP/NIP patient"]))
        monkeypatch.setattr(
            chat_router, "ask_mispl",
            lambda *a, **kw: (calls.append(1), ("ne doit jamais arriver", []))[1],
        )

        resp = client.post("/chat/ask", json={"question": "IPP:1234567 quoi faire ?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["blocked"] is True
        assert body["dlp_alerts"] == ["IPP/NIP patient"]
        assert body["response"] is None
        assert calls == []


class TestSuccessfulAsk:
    def test_technicien_mode_passed_for_non_dsi_user(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory, can_use_dsi_mode=False)
        login(client)

        captured = {}

        def fake_ask_mispl(question, **kwargs):
            captured.update(kwargs)
            captured["question"] = question
            return "reponse test", [
                {"function_name": "Substr", "source": "doc.md", "score": 0.9, "exact_match": True}
            ]

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", fake_ask_mispl)

        resp = client.post("/chat/ask", json={"question": "Comment utiliser Substr ?"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["blocked"] is False
        assert body["response"] == "reponse test"
        assert body["sources"][0]["function_name"] == "Substr"
        assert captured["access_mode"] == "technicien"

    def test_dsi_mode_passed_for_dsi_user(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory, email="dsi@labo.fr", can_use_dsi_mode=True)
        login(client, email="dsi@labo.fr")

        captured = {}

        def fake_ask_mispl(question, **kwargs):
            captured.update(kwargs)
            return "ok", []

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", fake_ask_mispl)

        resp = client.post("/chat/ask", json={"question": "Boucle WHILE ?"})
        assert resp.status_code == 200
        assert captured["access_mode"] == "dsi"

    def test_lab_context_enriches_question(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        captured = {}

        def fake_ask_mispl(question, **kwargs):
            captured["question"] = question
            return "ok", []

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", fake_ask_mispl)

        client.post(
            "/chat/ask",
            json={"question": "Formater la date ?", "lab_context": "Analyseur Cobas c702"},
        )
        assert "Analyseur Cobas c702" in captured["question"]
        assert "Formater la date ?" in captured["question"]


class TestLLMError:
    def test_ask_mispl_exception_returns_503(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        def raising_ask_mispl(*a, **kw):
            raise RuntimeError("OpenRouter down")

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", raising_ask_mispl)

        resp = client.post("/chat/ask", json={"question": "Comment utiliser Substr ?"})
        assert resp.status_code == 503
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_chat_routes.py -v`
Expected: FAIL avec `ModuleNotFoundError: No module named 'api.routers.chat'`

- [ ] **Step 3: Ajouter les schémas de chat à `api/schemas.py`**

Ajouter à la fin du fichier :

```python
class ChatRequest(BaseModel):
    question: str
    lab_context: str | None = None


class SourceOut(BaseModel):
    function_name: str
    source: str
    score: float
    exact_match: bool


class ChatResponse(BaseModel):
    response: str | None
    sources: list[SourceOut]
    blocked: bool
    dlp_alerts: list[str]
```

- [ ] **Step 4: Implémenter `api/routers/chat.py`**

```python
# api/routers/chat.py
"""Route de chat — encapsule ask_mispl() derrière l'authentification de compte."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.models import User
from api.schemas import ChatRequest, ChatResponse, SourceOut
from src.agent.mispl_agent import ask_mispl
from src.security.access_mode import access_mode_for_user
from src.security.dlp import dlp_check

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
def ask(payload: ChatRequest, user: User = Depends(get_current_user)):
    question_enriched = payload.question
    if payload.lab_context:
        question_enriched = f"[Contexte labo: {payload.lab_context.strip()}]\n\n{payload.question}"

    blocked, dlp_alerts = dlp_check(question_enriched)
    if blocked:
        return ChatResponse(response=None, sources=[], blocked=True, dlp_alerts=dlp_alerts)

    access_mode = access_mode_for_user(user.can_use_dsi_mode)

    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
        )
    except Exception:
        logger.exception("Erreur lors de l'appel ask_mispl")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporairement indisponible — réessayez dans quelques instants.",
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

    return ChatResponse(response=response_text, sources=sources, blocked=False, dlp_alerts=[])
```

- [ ] **Step 5: Enregistrer le routeur dans `api/main.py`**

```python
# api/main.py
"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import Base, engine
from api.routers import admin, auth, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MISPL Agent API", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
```

- [ ] **Step 6: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_chat_routes.py -v`
Expected: PASS (6 tests)

- [ ] **Step 7: Lancer la suite complète (vérifier l'absence de régression)**

Run: `pytest tests/ -v`
Expected: PASS (tous les tests existants + les 6 nouveaux)

- [ ] **Step 8: Commit**

```bash
git add api/routers/chat.py api/schemas.py api/main.py tests/api/test_chat_routes.py
git commit -m "feat(api): route /chat/ask — encapsule ask_mispl derrière l'auth de compte"
```

---

## Task 2: CORS pour le frontend Next.js

**Files:**
- Modify: `api/main.py`
- Test: `tests/api/test_cors.py`

**Interfaces:**
- Consumes: rien de nouveau
- Produces: en-têtes CORS sur toutes les réponses de l'API pour l'origine configurée (`MISPL_FRONTEND_ORIGIN`, défaut `http://localhost:3000`)

- [ ] **Step 1: Écrire le test**

```python
# tests/api/test_cors.py
"""Vérifie que l'API autorise le frontend Next.js en local (CORS + credentials)."""


class TestCORS:
    def test_allows_configured_frontend_origin_with_credentials(self, client, db_session_factory):
        resp = client.get("/auth/me", headers={"Origin": "http://localhost:3000"})
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert resp.headers.get("access-control-allow-credentials") == "true"
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `pytest tests/api/test_cors.py -v`
Expected: FAIL — `access-control-allow-origin` absent des en-têtes de réponse

- [ ] **Step 3: Ajouter le middleware CORS dans `api/main.py`**

```python
# api/main.py
"""Point d'entrée de l'API MISPL Agent."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import Base, engine
from api.routers import admin, auth, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="MISPL Agent API", lifespan=lifespan)

_frontend_origins = os.environ.get("MISPL_FRONTEND_ORIGIN", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
```

- [ ] **Step 4: Lancer le test, vérifier le succès**

Run: `pytest tests/api/test_cors.py -v`
Expected: PASS

- [ ] **Step 5: Lancer la suite complète**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add api/main.py tests/api/test_cors.py
git commit -m "feat(api): CORS pour le frontend Next.js (origine configurable via MISPL_FRONTEND_ORIGIN)"
```

---

## Task 3: Scaffold du projet Next.js + design tokens Quiet Luxury

**Files:**
- Create: `frontend/` (généré par `create-next-app`, puis modifié)
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Produces: variables CSS (`--bg`, `--surface`, `--ink`, `--ink-soft`, `--line`, `--accent`, `--accent-soft`, `--danger`, `--radius`, `--shadow`, `--serif`, `--sans`) utilisables dans toutes les pages/composants suivants ; classes utilitaires `.card`, `.error-banner`, styles `button`/`button.ghost`/`input`/`textarea` globaux

- [ ] **Step 1: Générer le projet Next.js**

Depuis la racine du dépôt (`C:\Users\flo40\Documents\MISPL\MISPL\MISPL`) :

```bash
npx --yes create-next-app@latest frontend --ts --no-tailwind --no-eslint --app --no-src-dir --import-alias "@/*" --use-npm --disable-git --yes
```

`--disable-git` est important : le dépôt racine a déjà son `.git`, `create-next-app` ne doit pas en initialiser un second dans `frontend/`.

Si des questions interactives apparaissent malgré les flags (différences de version) : TypeScript → Yes, Tailwind CSS → No, ESLint → No, App Router → Yes, dossier `src/` → No, alias d'import → garder la valeur par défaut proposée.

- [ ] **Step 2: Vérifier que le projet généré compile**

Run: `cd frontend && npm run build`
Expected: build réussi (page de démo Next.js par défaut)

- [ ] **Step 3: Remplacer `frontend/app/globals.css`**

```css
:root {
  --bg: #faf9f6;
  --surface: #ffffff;
  --ink: #1a1a1a;
  --ink-soft: #5c5c5c;
  --line: #e6e3dc;
  --accent: #6f7d6a;
  --accent-soft: #eef0ec;
  --danger: #a8584f;
  --radius: 14px;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.03), 0 8px 24px rgba(0, 0, 0, 0.04);
  --serif: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  --sans: "Inter", -apple-system, "Segoe UI", Roboto, sans-serif;
}

* {
  box-sizing: border-box;
}
html,
body {
  margin: 0;
  padding: 0;
}
body {
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

h1,
h2,
h3 {
  font-family: var(--serif);
  font-weight: 500;
  margin: 0;
}

.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px 24px;
}

button {
  font-family: inherit;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
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
  color: var(--accent);
}

input,
textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  font-family: inherit;
  font-size: 14px;
  background: var(--bg);
  color: var(--ink);
}

.error-banner {
  border-left: 3px solid var(--danger);
  background: #f6ece9;
  color: var(--ink);
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13.5px;
}
```

- [ ] **Step 4: Remplacer `frontend/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MISPL Agent",
  description: "Assistant IA pour le paramétrage GLIMS/MISPL",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 5: Remplacer `frontend/app/page.tsx`**

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}
```

- [ ] **Step 6: Vérifier que le build passe toujours**

Run: `cd frontend && npm run build`
Expected: build réussi (la redirection `/` → `/chat` ne casse pas le build même si `/chat` n'existe pas encore — Next.js compile chaque route indépendamment ; une visite manuelle donnera un 404 sur `/chat` jusqu'à la Task 5, c'est attendu à ce stade)

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js + design tokens Quiet Luxury"
```

---

## Task 4: Client API + page de connexion

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/.env.local.example`

**Interfaces:**
- Produces: `login(email, password) -> Promise<MeResponse>`, `logout() -> Promise<{detail: string}>`, `getMe() -> Promise<MeResponse>`, `askChat(question, labContext?) -> Promise<ChatResponse>`, classe `ApiError extends Error` avec `.status: number`, interfaces TypeScript `MeResponse`, `SourceOut`, `ChatResponse` — réutilisées par la Task 5

- [ ] **Step 1: Créer `frontend/.env.local.example`**

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- [ ] **Step 2: Implémenter `frontend/lib/api.ts`**

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // pas de corps JSON exploitable
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export interface MeResponse {
  id: number;
  email: string;
  display_name: string;
  platform_role: string;
  can_use_dsi_mode: boolean;
}

export function login(email: string, password: string): Promise<MeResponse> {
  return request<MeResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<{ detail: string }> {
  return request("/auth/logout", { method: "POST" });
}

export function getMe(): Promise<MeResponse> {
  return request<MeResponse>("/auth/me");
}

export interface SourceOut {
  function_name: string;
  source: string;
  score: number;
  exact_match: boolean;
}

export interface ChatResponse {
  response: string | null;
  sources: SourceOut[];
  blocked: boolean;
  dlp_alerts: string[];
}

export function askChat(question: string, labContext?: string): Promise<ChatResponse> {
  return request<ChatResponse>("/chat/ask", {
    method: "POST",
    body: JSON.stringify({ question, lab_context: labContext || undefined }),
  });
}
```

- [ ] **Step 3: Implémenter `frontend/app/login/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, ApiError } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/chat");
    } catch (err) {
      if (err instanceof ApiError && err.status === 423) {
        setError("Compte verrouillé temporairement — trop de tentatives. Réessayez dans 15 minutes.");
      } else {
        setError("Email ou mot de passe incorrect.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 380, margin: "10vh auto", padding: "0 20px" }}>
      <div className="card">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Assistant MISPL</h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 13, marginBottom: 20 }}>
          Connexion technicien
        </p>
        <form onSubmit={handleSubmit}>
          <label style={{ display: "block", fontSize: 12.5, color: "var(--ink-soft)", marginBottom: 6 }}>
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ marginBottom: 14 }}
          />
          <label style={{ display: "block", fontSize: 12.5, color: "var(--ink-soft)", marginBottom: 6 }}>
            Mot de passe
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ marginBottom: 14 }}
          />
          {error && (
            <div className="error-banner" style={{ marginBottom: 14 }}>
              {error}
            </div>
          )}
          <button type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi, aucune erreur TypeScript

- [ ] **Step 5: Vérification manuelle**

1. Copier `frontend/.env.local.example` en `frontend/.env.local`
2. Terminal 1 : depuis la racine du dépôt, `.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000`
3. Si aucun compte n'existe encore : `.venv\Scripts\python.exe scripts\create_admin.py` pour en créer un
4. Terminal 2 : `cd frontend && npm run dev`
5. Ouvrir `http://localhost:3000/login`
6. Saisir un mauvais mot de passe → la bannière d'erreur rouge s'affiche, pas de redirection
7. Saisir les bons identifiants → redirection vers `/chat` (404 attendu à ce stade, la page n'existe pas encore — Task 5). Vérifier dans les outils dev du navigateur (Application/Storage → Cookies) que le cookie `session_token` est bien posé sur `localhost:8000` avec `HttpOnly` coché

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/api.ts frontend/app/login/page.tsx frontend/.env.local.example
git commit -m "feat(frontend): client API + page de connexion"
```

---

## Task 5: Page de chat

**Files:**
- Create: `frontend/components/ChatMessage.tsx`
- Create: `frontend/components/EmptyState.tsx`
- Create: `frontend/app/chat/page.tsx`

**Interfaces:**
- Consumes: `login`, `logout`, `getMe`, `askChat`, `ApiError`, `MeResponse`, `SourceOut`, `ChatResponse` depuis `frontend/lib/api.ts` (Task 4)
- Produces: page `/chat` fonctionnelle — pas d'export consommé par une tâche ultérieure (dernière tâche du chantier A)

**Note de conception :** la spec suggérait un composant `SourcesPanel.tsx` séparé ; l'affichage des sources est finalement intégré directement dans `ChatMessage.tsx` (un `<details>` inline) — un fichier séparé n'apportait pas de séparation de responsabilité réelle pour un bloc aussi petit. Pas de nouvelle interface à documenter pour les tâches suivantes : le chantier B (historique) consommera l'API `/chat/ask` et les types de `lib/api.ts`, pas les composants internes de cette page.

- [ ] **Step 1: Implémenter `frontend/components/ChatMessage.tsx`**

```tsx
import { SourceOut } from "../lib/api";

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
}

export default function ChatMessage({ role, content, sources }: Props) {
  if (role === "user") {
    return (
      <div style={{ textAlign: "right", margin: "12px 0" }}>
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
      </div>
    );
  }

  return (
    <div style={{ margin: "12px 0" }}>
      <div className="card" style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.6 }}>
        {content}
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
  );
}
```

- [ ] **Step 2: Implémenter `frontend/components/EmptyState.tsx`**

```tsx
interface Props {
  examples: string[];
  onPick: (q: string) => void;
}

export default function EmptyState({ examples, onPick }: Props) {
  return (
    <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
      <p style={{ fontSize: 16, fontWeight: 500, color: "var(--ink-soft)", marginBottom: 20 }}>
        Posez votre première question MISPL
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, textAlign: "left" }}>
        {examples.map((ex) => (
          <button key={ex} className="ghost" onClick={() => onPick(ex)} style={{ fontSize: 13 }}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Implémenter `frontend/app/chat/page.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { askChat, getMe, logout, ApiError, MeResponse, SourceOut } from "../../lib/api";
import ChatMessage from "../../components/ChatMessage";
import EmptyState from "../../components/EmptyState";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceOut[];
}

const EXAMPLES = [
  "Comment utiliser Substr pour extraire une sous-chaine ?",
  "Comment formater la date du jour en MISPL ?",
  "Comment écrire un log d'audit avec AddLogEntry ?",
  "Comment récupérer l'utilisateur connecté ?",
];

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<MeResponse | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [labContext, setLabContext] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleAsk(q: string) {
    if (!q.trim() || loading) return;
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const result = await askChat(q, labContext || undefined);
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
          { role: "assistant", content: result.response ?? "", sources: result.sources },
        ]);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.push("/login");
        return;
      }
      const refId = Math.random().toString(36).slice(2, 10);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Service temporairement indisponible. Réessayez dans quelques instants. (Référence : ${refId})`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setMessages([]);
  }

  async function handleLogout() {
    await logout().catch(() => {});
    router.push("/login");
  }

  if (!user) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  return (
    <main style={{ maxWidth: 780, margin: "0 auto", padding: "2rem 1.5rem 6rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22 }}>Assistant MISPL</h1>
          <p style={{ color: "var(--ink-soft)", fontSize: 13 }}>{user.display_name}</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="ghost" onClick={handleReset}>
            Nouvelle conversation
          </button>
          <button className="ghost" onClick={handleLogout}>
            Déconnexion
          </button>
        </div>
      </header>

      {messages.length === 0 ? (
        <EmptyState examples={EXAMPLES} onPick={handleAsk} />
      ) : (
        <div>
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} sources={m.sources} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}

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
    </main>
  );
}
```

- [ ] **Step 4: Vérifier que le build passe**

Run: `cd frontend && npm run build`
Expected: build réussi, aucune erreur TypeScript

- [ ] **Step 5: Vérification manuelle complète du chantier A**

Avec les deux serveurs lancés (uvicorn :8000, `npm run dev` :3000) :

1. Aller sur `http://localhost:3000/chat` sans être connecté → redirection vers `/login`
2. Se connecter avec un compte valide → arrivée sur `/chat`, état vide avec les 4 exemples de questions cliquables
3. Cliquer un exemple → la question part, la bulle utilisateur apparaît, puis la réponse assistant avec un panneau « Sources documentaires » dépliable
4. Taper une question contenant `IPP:1234567` → réponse bloquée avec le message DLP, pas d'appel LLM (vérifiable dans les logs du terminal uvicorn : pas de log de session dans `outputs/sessions/`)
5. Remplir le champ « Contexte labo », poser une question → vérifier dans les logs uvicorn ou `outputs/sessions/` que le contexte labo apparaît bien dans la question envoyée
6. Cliquer « Nouvelle conversation » → le fil de messages se vide, l'état vide réapparaît
7. Arrêter le serveur uvicorn (Ctrl+C dans son terminal), poser une question → message « Service temporairement indisponible » avec une référence, pas de crash de la page
8. Relancer uvicorn, cliquer « Déconnexion » → redirection vers `/login`, retour sur `/chat` redirige de nouveau vers `/login` (session bien coupée)
9. Se reconnecter avec un compte ayant `can_use_dsi_mode=True` (créé via `PATCH /admin/users/{id}` ou `scripts/create_admin.py`) et poser une question nécessitant une boucle — vérifier que la réponse contient du code avec `WHILE`/`REPEAT` si pertinent (pas bloqué). Se reconnecter avec un compte `can_use_dsi_mode=False` et poser la même question — vérifier le message de renvoi vers le mode DSI

- [ ] **Step 6: Commit**

```bash
git add frontend/components/ChatMessage.tsx frontend/components/EmptyState.tsx frontend/app/chat/page.tsx
git commit -m "feat(frontend): page de chat — messages, sources, contexte labo, gestion d'erreurs"
```
