# Chantier C — Dashboard admin et suivi de tokens — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire l'interface frontend du dashboard admin (déjà servi par une API existante) et ajouter un suivi de consommation de tokens par utilisateur (nouveau sous-système backend + affichage).

**Architecture:** Un paramètre de sortie optionnel `usage_out` sur `ask_mispl()` capture les tokens OpenRouter sans changer sa signature de retour (évite de casser une douzaine d'appelants existants). Une nouvelle table `UsageDaily` (une ligne par utilisateur et par jour) est alimentée depuis `api/routers/chat.py`. L'API admin existante s'enrichit de deux endpoints/champs pour exposer cet usage, et une nouvelle route `/admin` côté frontend consomme le tout.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, pytest, Next.js 16 (App Router, TypeScript, CSS pur, aucune dépendance de graphique).

**Spec:** `docs/superpowers/specs/2026-08-14-admin-dashboard-token-usage-design.md`

## Global Constraints

- `ask_mispl()` gagne un paramètre optionnel `usage_out: dict | None = None` en fin de signature — rétrocompatible, aucun appelant existant (`app.py`, `scripts/eval_*.py`, `scripts/health_check.py`, tests) n'est affecté.
- Sur un **cache hit** (retour anticipé avant tout appel LLM), `usage_out` doit être explicitement mis à zéro (`{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}`), pas laissé tel quel — aucun token n'a réellement été consommé.
- `UsageDaily` : contrainte unique `(user_id, date)`. Un message bloqué par le DLP n'appelle jamais `ask_mispl()` et ne doit créer/incrémenter aucune ligne — cohérent avec la persistance de conversation (chantier B).
- `AdminUserOut` (nouveau schéma, sous-classe de `UserOut` avec `total_tokens_30d`/`last_active_at`) est utilisé **uniquement** par `GET /admin/users`. Les endpoints `POST /admin/users`, `PATCH /admin/users/{id}`, `POST /admin/users/{id}/reset-password` gardent le schéma `UserOut` existant inchangé — évite tout risque sur leur contrat de réponse déjà testé.
- `GET /admin/users/{id}/usage-daily?days=N` retourne **toujours exactement N entrées**, une par jour calendaire dans la fenêtre, triées par date croissante, avec des zéros pour les jours sans activité (pas de jours absents) — condition nécessaire pour un graphique à espacement régulier.
- Le rôle (admin/user) est un badge en lecture seule dans le tableau — pas de bascule inline, seuls Mode DSI et Statut actif en ont une (le spec section C ne demande pas d'édition inline du rôle).
- Aucune nouvelle dépendance frontend : le graphique est en SVG inline fait main, comme les icônes déjà présentes (`AssistantAvatarIcon`, icônes de la sidebar) — pas de librairie de charting.
- Aucun framework de test frontend n'est configuré dans ce projet. Vérification via `npx tsc --noEmit` et `npm run build` (depuis `frontend/`), plus vérification manuelle décrite dans chaque tâche.
- `updateAdminUser()` (PATCH) retourne un objet **sans** `total_tokens_30d`/`last_active_at` (l'endpoint PATCH garde `UserOut`, pas `AdminUserOut`). Toute mise à jour optimiste côté frontend doit fusionner par spread (`{ ...previousRow, ...updated }`), jamais remplacer la ligne entière — sinon les colonnes tokens/dernière activité se videraient après une bascule.
- `last_active_at` est sérialisé par Pydantic comme une date pure `"YYYY-MM-DD"` (pas de composant horaire). Une chaîne de date pure (sans `T`) est interprétée comme UTC par `new Date(...)` en JavaScript (contrairement à une chaîne datetime sans offset, qui serait interprétée en heure locale — le bug corrigé dans `conversationGroups.ts` lors du chantier historique de sessions). `new Date(dateStr)` direct est donc correct ici, sans transformation supplémentaire.

## File Structure

**Backend :**
- Modifier `src/agent/mispl_agent.py` — paramètre `usage_out`, helper `_extract_usage`.
- Créer `tests/agent/test_usage.py` — tests de `_extract_usage`.
- Modifier `api/models.py` — modèle `UsageDaily`.
- Modifier `tests/api/test_models.py` — tests du modèle.
- Modifier `api/routers/chat.py` — capture et upsert de l'usage.
- Modifier `tests/api/test_chat_routes.py` — tests de la capture.
- Modifier `api/schemas.py` — `AdminUserOut`, `UsageDayOut`.
- Modifier `api/routers/admin.py` — `GET /admin/users` enrichi, nouvelle route `usage-daily`.
- Modifier `tests/api/test_admin_routes.py` — tests des extensions.

**Frontend :**
- Modifier `frontend/lib/api.ts` — client API admin.
- Créer `frontend/lib/format.ts` — formatage tokens/dates.
- Créer `frontend/components/Toggle.tsx` — bascule réutilisable.
- Modifier `frontend/components/AccountMenu.tsx` — lien Administration.
- Modifier `frontend/components/ConversationSidebar.tsx` — passe `isAdmin`.
- Modifier `frontend/app/chat/page.tsx` — calcule et passe `isAdmin`.
- Créer `frontend/app/admin/page.tsx` — page dashboard.
- Modifier `frontend/app/globals.css` — styles tableau/modal/bascule.
- Créer `frontend/components/UsageChart.tsx` — graphique SVG.
- Créer `frontend/components/AdminUserDetailPanel.tsx` — panneau de détail.

---

### Task 1: Capture des tokens dans `ask_mispl()` + modèle `UsageDaily`

**Files:**
- Modify: `src/agent/mispl_agent.py`
- Create: `tests/agent/test_usage.py`
- Modify: `api/models.py`
- Modify: `tests/api/test_models.py`

**Interfaces:**
- Produces : `ask_mispl(..., usage_out: dict | None = None)` — quand fourni, peuplé avec `{"prompt_tokens", "completion_tokens", "total_tokens"}` (zéros sur cache hit). Fonction privée `_extract_usage(completion) -> dict`. Modèle `UsageDaily(id, user_id, date, prompt_tokens, completion_tokens, request_count)` — consommés par Task 2/3.

- [ ] **Step 1: Écrire les tests de `_extract_usage`**

Créer `tests/agent/test_usage.py` :

```python
"""Tests de l'extraction des compteurs de tokens depuis une réponse OpenRouter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.mispl_agent import _extract_usage


class FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens, total_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class FakeCompletion:
    def __init__(self, usage):
        self.usage = usage


class TestExtractUsage:
    def test_reads_token_counts_from_completion(self):
        completion = FakeCompletion(FakeUsage(120, 340, 460))
        assert _extract_usage(completion) == {
            "prompt_tokens": 120,
            "completion_tokens": 340,
            "total_tokens": 460,
        }

    def test_defaults_to_zero_when_usage_missing(self):
        class NoUsage:
            pass

        assert _extract_usage(NoUsage()) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def test_defaults_to_zero_when_usage_is_none(self):
        completion = FakeCompletion(None)
        assert _extract_usage(completion) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/agent/test_usage.py -v`
Expected: FAIL (`ImportError: cannot import name '_extract_usage'`)

- [ ] **Step 3: Ajouter `_extract_usage` et le paramètre `usage_out` dans `mispl_agent.py`**

Ajouter cette fonction juste après `_call_with_fallback` (avant `# ── Core agent`, vers la ligne 352) :

```python
def _extract_usage(completion) -> dict:
    """Extrait les compteurs de tokens d'un objet completion OpenAI-compatible.
    Retourne des zéros si absent (ne devrait pas arriver hors tests, mais
    OpenRouter ne garantit pas formellement le champ pour tous les modèles)."""
    usage = getattr(completion, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "total_tokens": getattr(usage, "total_tokens", 0) or 0,
    }
```

Modifier la signature de `ask_mispl` (ligne ~355) pour ajouter le paramètre en dernière position :

```python
def ask_mispl(
    question: str,
    use_openai_embeddings: bool = False,
    top_k: int = DEFAULT_TOP_K,
    model: str = DEFAULT_MODEL,
    skill_profile: list[str] | None = None,
    save_session: bool = True,
    conversation_history: list[dict] | None = None,
    api_key: str | None = None,
    access_mode: str = MODE_DSI,
    usage_out: dict | None = None,
) -> tuple[str, list]:
```

Dans la docstring de `ask_mispl`, repérer :

```
        access_mode: "dsi" (génération complète) ou "technicien" (bridé — pas
            de boucles WHILE/REPEAT, cf. src/security/access_mode.py)

    Returns:
```

Le remplacer par :

```
        access_mode: "dsi" (génération complète) ou "technicien" (bridé — pas
            de boucles WHILE/REPEAT, cf. src/security/access_mode.py)
        usage_out: si fourni, rempli avec {"prompt_tokens", "completion_tokens",
            "total_tokens"} après l'appel LLM (zéros si réponse servie depuis
            le cache — aucun appel OpenRouter n'a eu lieu).

    Returns:
```

Repérer le cache hit (ligne ~396) :

```python
    _cached = _cache_get(_key)
    if _cached:
        logger.info(f"Cache hit pour question ({_key})")
        return _cached
```

Le remplacer par :

```python
    _cached = _cache_get(_key)
    if _cached:
        logger.info(f"Cache hit pour question ({_key})")
        if usage_out is not None:
            usage_out.update({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        return _cached
```

Repérer l'appel LLM (ligne ~436) :

```python
    used_model, completion = _call_with_fallback(client, model, messages, stream=False)
    response = completion.choices[0].message.content or ""
```

Le remplacer par :

```python
    used_model, completion = _call_with_fallback(client, model, messages, stream=False)
    if usage_out is not None:
        usage_out.update(_extract_usage(completion))
    response = completion.choices[0].message.content or ""
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/agent/test_usage.py -v`
Expected: PASS (3/3)

- [ ] **Step 5: Écrire le test du modèle `UsageDaily`**

Ajouter à l'import en haut de `tests/api/test_models.py` (remplacer la ligne existante) :

```python
from api.models import Conversation, Message, UsageDaily, User, UserSession
```

Ajouter `import datetime` s'il n'est pas déjà présent en haut du fichier (il l'est déjà, ligne 3).

Ajouter à la fin du fichier `tests/api/test_models.py` :

```python


class TestUsageDailyModel:
    def test_create_and_query_usage_row(self):
        db = make_session()
        user = User(email="tech6@labo.fr", password_hash="h", display_name="Tech Six", platform_role="user")
        db.add(user)
        db.commit()

        today = datetime.date.today()
        db.add(
            UsageDaily(
                user_id=user.id, date=today,
                prompt_tokens=100, completion_tokens=50, request_count=1,
            )
        )
        db.commit()

        fetched = db.query(UsageDaily).filter(UsageDaily.user_id == user.id).one()
        assert fetched.date == today
        assert fetched.prompt_tokens == 100
        assert fetched.completion_tokens == 50
        assert fetched.request_count == 1

    def test_unique_constraint_on_user_and_date(self):
        db = make_session()
        user = User(email="tech7@labo.fr", password_hash="h", display_name="Tech Sept", platform_role="user")
        db.add(user)
        db.commit()

        today = datetime.date.today()
        db.add(UsageDaily(user_id=user.id, date=today, prompt_tokens=10, completion_tokens=5, request_count=1))
        db.commit()

        db.add(UsageDaily(user_id=user.id, date=today, prompt_tokens=20, completion_tokens=10, request_count=1))
        import pytest
        with pytest.raises(Exception):
            db.commit()
```

- [ ] **Step 6: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_models.py -v -k UsageDaily`
Expected: FAIL (`ImportError: cannot import name 'UsageDaily'`)

- [ ] **Step 7: Ajouter le modèle `UsageDaily` dans `api/models.py`**

Modifier l'import en haut du fichier — remplacer :

```python
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
```

par :

```python
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
```

Ajouter à la fin du fichier `api/models.py` :

```python


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_usage_daily_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

- [ ] **Step 8: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_models.py -v`
Expected: PASS (tous, y compris les tests préexistants)

- [ ] **Step 9: Lancer toute la suite backend pour vérifier l'absence de régression**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS (tous les tests existants restent verts)

- [ ] **Step 10: Commit**

```bash
git add src/agent/mispl_agent.py tests/agent/test_usage.py api/models.py tests/api/test_models.py
git commit -m "feat(backend): capture des tokens OpenRouter et modèle UsageDaily"
```

---

### Task 2: Enregistrement de l'usage dans `POST /chat/ask`

**Files:**
- Modify: `api/routers/chat.py`
- Modify: `tests/api/test_chat_routes.py`

**Interfaces:**
- Consumes : `ask_mispl(..., usage_out=...)`, modèle `UsageDaily` (Task 1).
- Produces : ligne `UsageDaily` créée/incrémentée à chaque tour réussi et non bloqué par le DLP — consommée par Task 3 (agrégation admin).

- [ ] **Step 1: Écrire les tests de capture d'usage**

Modifier l'import en haut de `tests/api/test_chat_routes.py` — remplacer :

```python
from api.models import Conversation, Message, User
```

par :

```python
import datetime

from api.models import Conversation, Message, UsageDaily, User
```

Ajouter à la fin du fichier `tests/api/test_chat_routes.py` :

```python


class TestUsageTracking:
    def test_successful_ask_records_usage_for_today(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        def fake_ask_mispl(question, **kwargs):
            if kwargs.get("usage_out") is not None:
                kwargs["usage_out"].update(
                    {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
                )
            return "reponse", []

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", fake_ask_mispl)

        resp = client.post("/chat/ask", json={"question": "Comment utiliser Substr ?"})
        assert resp.status_code == 200

        db = db_session_factory()
        user = db.query(User).filter(User.email == "tech@labo.fr").one()
        today = datetime.datetime.utcnow().date()
        row = (
            db.query(UsageDaily)
            .filter(UsageDaily.user_id == user.id, UsageDaily.date == today)
            .one()
        )
        assert row.prompt_tokens == 100
        assert row.completion_tokens == 50
        assert row.request_count == 1

    def test_second_ask_same_day_increments_existing_row(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        def fake_ask_mispl(question, **kwargs):
            if kwargs.get("usage_out") is not None:
                kwargs["usage_out"].update(
                    {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                )
            return "ok", []

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (False, []))
        monkeypatch.setattr(chat_router, "ask_mispl", fake_ask_mispl)

        client.post("/chat/ask", json={"question": "Question 1 ?"})
        client.post("/chat/ask", json={"question": "Question 2 ?"})

        db = db_session_factory()
        user = db.query(User).filter(User.email == "tech@labo.fr").one()
        today = datetime.datetime.utcnow().date()
        rows = (
            db.query(UsageDaily)
            .filter(UsageDaily.user_id == user.id, UsageDaily.date == today)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].prompt_tokens == 20
        assert rows[0].completion_tokens == 10
        assert rows[0].request_count == 2

    def test_blocked_dlp_message_does_not_record_usage(self, client, db_session_factory, monkeypatch):
        make_user(db_session_factory)
        login(client)

        monkeypatch.setattr(chat_router, "dlp_check", lambda text: (True, ["IPP/NIP patient"]))
        monkeypatch.setattr(
            chat_router, "ask_mispl",
            lambda *a, **kw: (_ for _ in ()).throw(AssertionError("ne doit jamais être appelé")),
        )

        resp = client.post("/chat/ask", json={"question": "IPP:1234567 quoi faire ?"})
        assert resp.status_code == 200
        assert resp.json()["blocked"] is True

        db = db_session_factory()
        assert db.query(UsageDaily).count() == 0
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_chat_routes.py -v -k TestUsageTracking`
Expected: FAIL (`UsageDaily` jamais créé — la table reste vide)

- [ ] **Step 3: Modifier `api/routers/chat.py`**

Modifier l'import en haut du fichier — remplacer :

```python
from api.models import Conversation, Message, User
```

par :

```python
from api.models import Conversation, Message, UsageDaily, User
```

Ajouter cette fonction juste après `_make_title` (avant `@router.post("/ask"...)`) :

```python
def _record_usage(db: DBSession, user_id: int, usage: dict) -> None:
    today = datetime.datetime.utcnow().date()
    row = (
        db.query(UsageDaily)
        .filter(UsageDaily.user_id == user_id, UsageDaily.date == today)
        .first()
    )
    if row is None:
        row = UsageDaily(user_id=user_id, date=today, prompt_tokens=0, completion_tokens=0, request_count=0)
        db.add(row)
    row.prompt_tokens += usage.get("prompt_tokens", 0)
    row.completion_tokens += usage.get("completion_tokens", 0)
    row.request_count += 1
```

Dans la fonction `ask`, repérer l'appel à `ask_mispl` :

```python
    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
            conversation_history=history,
        )
    except Exception:
```

Le remplacer par :

```python
    usage: dict = {}
    try:
        response_text, docs = ask_mispl(
            question_enriched,
            access_mode=access_mode,
            save_session=True,
            conversation_history=history,
            usage_out=usage,
        )
    except Exception:
```

Repérer la fin de la fonction, juste avant `conversation.updated_at = now` :

```python
    conversation.updated_at = now
    db.commit()
```

La remplacer par :

```python
    conversation.updated_at = now
    _record_usage(db, user.id, usage)
    db.commit()
```

- [ ] **Step 4: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_chat_routes.py -v`
Expected: PASS (tous les tests, y compris ceux préexistants sur DLP/conversation)

- [ ] **Step 5: Lancer toute la suite backend pour vérifier l'absence de régression**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add api/routers/chat.py tests/api/test_chat_routes.py
git commit -m "feat(api): enregistre l'usage de tokens par jour dans POST /chat/ask"
```

---

### Task 3: Extensions API admin — usage agrégé et série quotidienne

**Files:**
- Modify: `api/schemas.py`
- Modify: `api/routers/admin.py`
- Modify: `tests/api/test_admin_routes.py`

**Interfaces:**
- Consumes : modèle `UsageDaily` (Task 1/2).
- Produces : schéma `AdminUserOut` (sous-classe de `UserOut` + `total_tokens_30d: int`, `last_active_at: datetime.date | None`) ; schéma `UsageDayOut(date, prompt_tokens, completion_tokens, request_count)` ; route `GET /admin/users/{user_id}/usage-daily?days=N` retournant `list[UsageDayOut]` de longueur exactement `N`, zéro-remplie — consommés par Task 4 (client frontend).

- [ ] **Step 1: Écrire les tests des extensions admin**

Ajouter à l'import en haut de `tests/api/test_admin_routes.py` — remplacer :

```python
from api.models import User
```

par :

```python
import datetime

from api.models import UsageDaily, User
```

Ajouter à la fin du fichier `tests/api/test_admin_routes.py` :

```python


def add_usage(db_session_factory, user_id, date, prompt_tokens, completion_tokens, request_count=1):
    db = db_session_factory()
    db.add(
        UsageDaily(
            user_id=user_id, date=date,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            request_count=request_count,
        )
    )
    db.commit()
    db.close()


class TestListUsersUsageFields:
    def test_new_user_has_zero_usage_and_no_last_active(self, client, db_session_factory):
        make_admin(db_session_factory)
        make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.get("/admin/users")
        assert resp.status_code == 200
        tech = next(u for u in resp.json() if u["email"] == "tech@labo.fr")
        assert tech["total_tokens_30d"] == 0
        assert tech["last_active_at"] is None

    def test_usage_aggregated_over_30_days(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        today = datetime.date.today()
        add_usage(db_session_factory, user.id, today, prompt_tokens=100, completion_tokens=50)
        add_usage(db_session_factory, user.id, today - datetime.timedelta(days=5), prompt_tokens=30, completion_tokens=20)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.get("/admin/users")
        tech = next(u for u in resp.json() if u["email"] == "tech@labo.fr")
        assert tech["total_tokens_30d"] == 200
        assert tech["last_active_at"] == today.isoformat()

    def test_usage_older_than_30_days_excluded(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        old_date = datetime.date.today() - datetime.timedelta(days=45)
        add_usage(db_session_factory, user.id, old_date, prompt_tokens=999, completion_tokens=999)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.get("/admin/users")
        tech = next(u for u in resp.json() if u["email"] == "tech@labo.fr")
        assert tech["total_tokens_30d"] == 0


class TestUsageDailyRoute:
    def test_returns_window_length_zero_filled(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        today = datetime.date.today()
        add_usage(db_session_factory, user.id, today, prompt_tokens=100, completion_tokens=50, request_count=2)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.get(f"/admin/users/{user.id}/usage-daily?days=7")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 7
        assert body[-1]["date"] == today.isoformat()
        assert body[-1]["prompt_tokens"] == 100
        assert body[-1]["request_count"] == 2
        assert body[0]["prompt_tokens"] == 0
        assert body[0]["request_count"] == 0

    def test_chronological_order(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.get(f"/admin/users/{user.id}/usage-daily?days=5")
        dates = [row["date"] for row in resp.json()]
        assert dates == sorted(dates)

    def test_404_for_nonexistent_user(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.get("/admin/users/999/usage-daily")
        assert resp.status_code == 404

    def test_403_for_non_admin(self, client, db_session_factory):
        user = make_regular_user(db_session_factory)
        login_as(client, "tech@labo.fr", "TechMdp1!")
        resp = client.get(f"/admin/users/{user.id}/usage-daily")
        assert resp.status_code == 403
```

- [ ] **Step 2: Lancer les tests pour vérifier qu'ils échouent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_admin_routes.py -v -k "UsageFields or UsageDaily"`
Expected: FAIL (`total_tokens_30d` absent de la réponse, route `usage-daily` inexistante → 404 générique au lieu du comportement attendu)

- [ ] **Step 3: Ajouter les schémas dans `api/schemas.py`**

Ajouter à la fin du fichier `api/schemas.py` :

```python


class AdminUserOut(UserOut):
    total_tokens_30d: int = 0
    last_active_at: datetime.date | None = None


class UsageDayOut(BaseModel):
    date: datetime.date
    prompt_tokens: int
    completion_tokens: int
    request_count: int
```

- [ ] **Step 4: Modifier `api/routers/admin.py`**

Modifier les imports en haut du fichier — remplacer :

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import require_admin
from api.models import User
from api.schemas import (
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    RevokeSessionsResponse,
    UpdateUserRequest,
    UserOut,
)
from api.security import generate_temp_password, hash_password
from api.session_store import revoke_all_sessions_for_user
```

par :

```python
import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from api.db import get_db
from api.dependencies import require_admin
from api.models import UsageDaily, User
from api.schemas import (
    AdminUserOut,
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    RevokeSessionsResponse,
    UpdateUserRequest,
    UsageDayOut,
    UserOut,
)
from api.security import generate_temp_password, hash_password
from api.session_store import revoke_all_sessions_for_user
```

Remplacer la fonction `list_users` existante :

```python
@router.get("/users", response_model=list[UserOut])
def list_users(db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()
```

par :

```python
@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: DBSession = Depends(get_db), _admin: User = Depends(require_admin)):
    users = db.query(User).order_by(User.id).all()

    cutoff = datetime.datetime.utcnow().date() - datetime.timedelta(days=30)
    rows = (
        db.query(
            UsageDaily.user_id,
            func.sum(UsageDaily.prompt_tokens + UsageDaily.completion_tokens).label("total_tokens"),
            func.max(UsageDaily.date).label("last_active"),
        )
        .filter(UsageDaily.date >= cutoff)
        .group_by(UsageDaily.user_id)
        .all()
    )
    usage_by_user = {r.user_id: (r.total_tokens or 0, r.last_active) for r in rows}

    result = []
    for u in users:
        total_tokens, last_active = usage_by_user.get(u.id, (0, None))
        result.append(
            AdminUserOut(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                platform_role=u.platform_role,
                can_use_dsi_mode=u.can_use_dsi_mode,
                is_active=u.is_active,
                total_tokens_30d=total_tokens,
                last_active_at=last_active,
            )
        )
    return result
```

Ajouter à la fin du fichier `api/routers/admin.py` :

```python


@router.get("/users/{user_id}/usage-daily", response_model=list[UsageDayOut])
def get_usage_daily(
    user_id: int,
    days: int = 30,
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    _get_user_or_404(db, user_id)

    today = datetime.datetime.utcnow().date()
    start = today - datetime.timedelta(days=days - 1)
    rows = (
        db.query(UsageDaily)
        .filter(UsageDaily.user_id == user_id, UsageDaily.date >= start)
        .all()
    )
    by_date = {r.date: r for r in rows}

    result = []
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        row = by_date.get(d)
        result.append(
            UsageDayOut(
                date=d,
                prompt_tokens=row.prompt_tokens if row else 0,
                completion_tokens=row.completion_tokens if row else 0,
                request_count=row.request_count if row else 0,
            )
        )
    return result
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/api/test_admin_routes.py -v`
Expected: PASS (tous les tests, y compris ceux préexistants sur création/modification/reset)

- [ ] **Step 6: Lancer toute la suite backend pour vérifier l'absence de régression**

Run: `C:\Users\flo40\Documents\MISPL\MISPL\MISPL\.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add api/schemas.py api/routers/admin.py tests/api/test_admin_routes.py
git commit -m "feat(api): usage agrégé sur GET /admin/users et route usage-daily"
```

---

### Task 4: Client API admin (frontend) et point d'entrée

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/lib/format.ts`
- Modify: `frontend/components/AccountMenu.tsx`
- Modify: `frontend/components/ConversationSidebar.tsx`
- Modify: `frontend/app/chat/page.tsx`

**Interfaces:**
- Consumes : `GET/POST/PATCH /admin/users*`, `GET /admin/users/{id}/usage-daily` (Task 3).
- Produces : `UserBase`, `AdminUser`, `CreateUserResult`, `UpdateUserPayload`, `UsageDay`, `listAdminUsers()`, `createAdminUser()`, `updateAdminUser()`, `resetAdminPassword()`, `revokeAdminSessions()`, `getUserUsageDaily()` dans `frontend/lib/api.ts` ; `formatTokenCount()`, `formatLastActive()` dans `frontend/lib/format.ts` — consommés par Task 5/6. `AccountMenu` gagne une prop `isAdmin?: boolean`.

- [ ] **Step 1: Ajouter le client API admin dans `frontend/lib/api.ts`**

Ajouter à la fin du fichier `frontend/lib/api.ts` :

```typescript

export interface UserBase {
  id: number;
  email: string;
  display_name: string;
  platform_role: string;
  can_use_dsi_mode: boolean;
  is_active: boolean;
}

export interface AdminUser extends UserBase {
  total_tokens_30d: number;
  last_active_at: string | null;
}

export interface CreateUserResult extends UserBase {
  temporary_password: string;
}

export interface UpdateUserPayload {
  display_name?: string;
  platform_role?: string;
  can_use_dsi_mode?: boolean;
  is_active?: boolean;
}

export interface UsageDay {
  date: string;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
}

export function listAdminUsers(): Promise<AdminUser[]> {
  return request<AdminUser[]>("/admin/users");
}

export function createAdminUser(payload: {
  email: string;
  display_name: string;
  platform_role: string;
  can_use_dsi_mode: boolean;
}): Promise<CreateUserResult> {
  return request<CreateUserResult>("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAdminUser(id: number, payload: UpdateUserPayload): Promise<UserBase> {
  return request<UserBase>(`/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function resetAdminPassword(id: number): Promise<{ temporary_password: string }> {
  return request<{ temporary_password: string }>(`/admin/users/${id}/reset-password`, {
    method: "POST",
  });
}

export function revokeAdminSessions(id: number): Promise<{ revoked: number }> {
  return request<{ revoked: number }>(`/admin/users/${id}/revoke-sessions`, {
    method: "POST",
  });
}

export function getUserUsageDaily(id: number, days = 30): Promise<UsageDay[]> {
  return request<UsageDay[]>(`/admin/users/${id}/usage-daily?days=${days}`);
}
```

- [ ] **Step 2: Créer `frontend/lib/format.ts`**

```typescript
export function formatTokenCount(n: number): string {
  if (n < 1000) return String(n);
  return `${(n / 1000).toFixed(1).replace(".", ",")}k`;
}

export function formatLastActive(dateStr: string | null): string {
  if (!dateStr) return "Jamais";
  const date = new Date(dateStr);
  const today = new Date();
  const diffDays = Math.floor(
    (Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()) -
      Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())) /
      86400000
  );
  if (diffDays <= 0) return "Aujourd'hui";
  if (diffDays === 1) return "Hier";
  return `Il y a ${diffDays} j`;
}
```

- [ ] **Step 3: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 4: Ajouter le lien Administration dans `AccountMenu.tsx`**

Ajouter l'import en haut du fichier, après les imports existants :

```tsx
import Link from "next/link";
```

Modifier l'interface `Props` :

```tsx
interface Props {
  displayName: string;
  onLogout: () => void;
  compact?: boolean;
  isAdmin?: boolean;
}
```

Modifier la signature du composant :

```tsx
export default function AccountMenu({ displayName, onLogout, compact = false, isAdmin = false }: Props) {
```

Dans le panneau déroulant, juste avant le bouton « Déconnexion », ajouter :

```tsx
          {isAdmin && (
            <Link
              href="/admin"
              style={{
                display: "block",
                padding: "8px 0",
                fontSize: 13.5,
                color: "var(--ink)",
                textDecoration: "none",
                borderTop: "1px solid var(--line)",
                marginTop: 4,
                marginBottom: 4,
              }}
            >
              Administration
            </Link>
          )}
```

- [ ] **Step 5: Passer `isAdmin` à travers `ConversationSidebar.tsx`**

Modifier l'interface `Props` — ajouter :

```tsx
  isAdmin: boolean;
```

Modifier la signature du composant pour destructurer `isAdmin` avec les autres props.

Modifier les deux usages de `AccountMenu` dans le fichier (version repliée et version dépliée) pour leur passer `isAdmin={isAdmin}`.

- [ ] **Step 6: Passer `isAdmin` depuis `chat/page.tsx`**

Repérer l'usage de `<ConversationSidebar ... onLogout={handleLogout} />` et ajouter la prop :

```tsx
        isAdmin={user.platform_role === "admin"}
```

- [ ] **Step 7: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 8: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 9: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/format.ts frontend/components/AccountMenu.tsx frontend/components/ConversationSidebar.tsx frontend/app/chat/page.tsx
git commit -m "feat(frontend): client API admin et lien d'accès au dashboard"
```

---

### Task 5: Page admin — tableau des comptes, création, bascules, actions

**Files:**
- Create: `frontend/components/Toggle.tsx`
- Create: `frontend/app/admin/page.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes : `listAdminUsers`, `createAdminUser`, `updateAdminUser`, `resetAdminPassword`, `revokeAdminSessions`, `AdminUser`, `UserBase`, `formatTokenCount`, `formatLastActive` (Task 4).
- Produces : `Toggle({ checked, onChange, label })`, exporté par défaut — consommé par Task 6 si besoin de cohérence visuelle. Page `/admin` complète, sans encore le clic-pour-détail (Task 6).

- [ ] **Step 1: Créer `frontend/components/Toggle.tsx`**

```tsx
interface Props {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
}

export default function Toggle({ checked, onChange, label }: Props) {
  return (
    <label className="toggle" aria-label={label}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-track" />
      <span className="toggle-thumb" />
    </label>
  );
}
```

- [ ] **Step 2: Ajouter les styles admin dans `frontend/app/globals.css`**

Ajouter à la fin du fichier `frontend/app/globals.css` :

```css

/* ── Bascule (toggle) ──────────────────────────────────────────── */

.toggle {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  cursor: pointer;
}
.toggle input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-track {
  position: absolute;
  inset: 0;
  background: var(--line);
  border-radius: 999px;
  transition: background 0.15s ease;
}
.toggle input:checked + .toggle-track {
  background: var(--accent-solid);
}
.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: #ffffff;
  border-radius: 50%;
  transition: transform 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  pointer-events: none;
}
.toggle input:checked ~ .toggle-thumb {
  transform: translateX(16px);
}

/* ── Dashboard admin ───────────────────────────────────────────── */

.admin-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 2rem 1.5rem 3rem;
}
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.admin-table-wrapper {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  overflow: hidden;
}
.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.admin-table th {
  text-align: left;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-soft);
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
}
.admin-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  vertical-align: middle;
}
.admin-table tr:last-child td {
  border-bottom: none;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--ink-soft);
}
.role-badge.admin {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-text);
}

.link-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  padding: 0;
  text-align: left;
  color: inherit;
}
.link-cell:hover {
  opacity: 1;
}
.link-cell:hover .link-cell-name {
  text-decoration: underline;
}

/* ── Modal ─────────────────────────────────────────────────────── */

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 26, 26, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 20px;
}
.modal-card {
  width: 100%;
  max-width: 420px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}
.field-label {
  display: block;
  font-size: 12px;
  color: var(--ink-soft);
  margin-bottom: 6px;
}
```

- [ ] **Step 3: Créer `frontend/app/admin/page.tsx`**

```tsx
"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getMe,
  listAdminUsers,
  createAdminUser,
  updateAdminUser,
  resetAdminPassword,
  revokeAdminSessions,
  ApiError,
  MeResponse,
  AdminUser,
} from "../../lib/api";
import { getInitials } from "../../lib/avatar";
import { formatTokenCount, formatLastActive } from "../../lib/format";
import UserAvatarBadge from "../../components/UserAvatarBadge";
import Toggle from "../../components/Toggle";

function CreateUserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (user: AdminUser, tempPassword: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [platformRole, setPlatformRole] = useState("user");
  const [canUseDsiMode, setCanUseDsiMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await createAdminUser({
        email,
        display_name: displayName,
        platform_role: platformRole,
        can_use_dsi_mode: canUseDsiMode,
      });
      const { temporary_password, ...user } = result;
      onCreated({ ...user, total_tokens_30d: 0, last_active_at: null }, temporary_password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Échec de la création du compte");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card modal-card" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ fontSize: 17, marginBottom: 16 }}>Nouveau compte</h2>
        {error && (
          <div className="error-banner" style={{ marginBottom: 12 }}>
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <label className="field-label">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ marginBottom: 12 }}
          />
          <label className="field-label">Nom affiché</label>
          <input
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            style={{ marginBottom: 12 }}
          />
          <label className="field-label">Rôle</label>
          <select
            value={platformRole}
            onChange={(e) => setPlatformRole(e.target.value)}
            style={{ marginBottom: 12 }}
          >
            <option value="user">Utilisateur</option>
            <option value="admin">Administrateur</option>
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18, fontSize: 13.5 }}>
            <input
              type="checkbox"
              checked={canUseDsiMode}
              onChange={(e) => setCanUseDsiMode(e.target.checked)}
              style={{ width: "auto" }}
            />
            Accès mode DSI
          </label>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button type="button" className="ghost" onClick={onClose}>
              Annuler
            </button>
            <button type="submit" disabled={submitting}>
              {submitting ? "..." : "Créer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [me, setMe] = useState<MeResponse | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [tempPasswordBanner, setTempPasswordBanner] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    getMe()
      .then((m) => {
        if (m.platform_role !== "admin") {
          router.push("/chat");
          return;
        }
        setMe(m);
      })
      .catch(() => router.push("/login?expired=1"));
  }, [router]);

  useEffect(() => {
    if (me) refreshUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me]);

  async function refreshUsers() {
    try {
      const list = await listAdminUsers();
      setUsers(list);
      setLoadError(null);
    } catch {
      setLoadError("Impossible de charger la liste des comptes");
    }
  }

  async function handleToggle(id: number, field: "can_use_dsi_mode" | "is_active", value: boolean) {
    const previous = users;
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, [field]: value } : u)));
    setActionError(null);
    try {
      const updated = await updateAdminUser(id, { [field]: value });
      setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, ...updated } : u)));
    } catch (err) {
      setUsers(previous);
      setActionError(err instanceof ApiError ? err.message : "Échec de la mise à jour");
    }
  }

  async function handleResetPassword(id: number) {
    setActionError(null);
    try {
      const result = await resetAdminPassword(id);
      setTempPasswordBanner(`Nouveau mot de passe temporaire : ${result.temporary_password}`);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Échec de la réinitialisation");
    }
  }

  async function handleRevokeSessions(id: number) {
    setActionError(null);
    try {
      await revokeAdminSessions(id);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Échec de la révocation des sessions");
    }
  }

  if (!me) {
    return <main style={{ padding: 40 }}>Chargement...</main>;
  }

  return (
    <main className="admin-page">
      <div className="admin-header">
        <h1 style={{ fontSize: 22 }}>Administration</h1>
        <button onClick={() => setShowCreateModal(true)}>+ Nouveau compte</button>
      </div>

      {tempPasswordBanner && (
        <div className="warning-banner" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", gap: 12 }}>
          <span>{tempPasswordBanner}</span>
          <button className="ghost" onClick={() => setTempPasswordBanner(null)} style={{ padding: "2px 10px", fontSize: 12 }}>
            OK
          </button>
        </div>
      )}
      {actionError && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          {actionError}
        </div>
      )}
      {loadError && (
        <div className="error-banner" style={{ marginBottom: 16 }}>
          {loadError}
        </div>
      )}

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Compte</th>
              <th>Rôle</th>
              <th>Mode DSI</th>
              <th>Actif</th>
              <th>Tokens (30j)</th>
              <th>Dernière activité</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <UserAvatarBadge initials={getInitials(u.display_name)} size={28} />
                    <div>
                      <div style={{ fontSize: 13.5 }}>{u.display_name}</div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-soft)" }}>{u.email}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`role-badge${u.platform_role === "admin" ? " admin" : ""}`}>
                    {u.platform_role === "admin" ? "Admin" : "Utilisateur"}
                  </span>
                </td>
                <td>
                  <Toggle
                    checked={u.can_use_dsi_mode}
                    onChange={(v) => handleToggle(u.id, "can_use_dsi_mode", v)}
                    label={`Mode DSI pour ${u.display_name}`}
                  />
                </td>
                <td>
                  <Toggle
                    checked={u.is_active}
                    onChange={(v) => handleToggle(u.id, "is_active", v)}
                    label={`Compte actif pour ${u.display_name}`}
                  />
                </td>
                <td>{formatTokenCount(u.total_tokens_30d)}</td>
                <td>{formatLastActive(u.last_active_at)}</td>
                <td>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      className="ghost"
                      onClick={() => handleResetPassword(u.id)}
                      style={{ fontSize: 12, padding: "6px 10px" }}
                    >
                      Réinitialiser
                    </button>
                    <button
                      className="ghost"
                      onClick={() => handleRevokeSessions(u.id)}
                      style={{ fontSize: 12, padding: "6px 10px" }}
                    >
                      Révoquer
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(user, tempPassword) => {
            setUsers((prev) => [...prev, user]);
            setTempPasswordBanner(`Mot de passe temporaire pour ${user.email} : ${tempPassword}`);
            setShowCreateModal(false);
          }}
        />
      )}
    </main>
  );
}
```

- [ ] **Step 4: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 5: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 6: Commit**

```bash
git add frontend/components/Toggle.tsx frontend/app/admin/page.tsx frontend/app/globals.css
git commit -m "feat(frontend): page dashboard admin (tableau, création, bascules, actions)"
```

---

### Task 6: Graphique de consommation et panneau de détail

**Files:**
- Create: `frontend/components/UsageChart.tsx`
- Create: `frontend/components/AdminUserDetailPanel.tsx`
- Modify: `frontend/app/admin/page.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes : `getUserUsageDaily`, `UsageDay`, `AdminUser` (Task 4), `formatTokenCount` (Task 4).
- Produces : `UsageChart({ userId, days? })`, `AdminUserDetailPanel({ user, onClose })` — intègrent la page admin de Task 5.

- [ ] **Step 1: Créer `frontend/components/UsageChart.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { getUserUsageDaily, UsageDay } from "../lib/api";

interface Props {
  userId: number;
  days?: number;
}

const CHART_HEIGHT = 120;
const BAR_MIN_HEIGHT = 3;

export default function UsageChart({ userId, days = 30 }: Props) {
  const [data, setData] = useState<UsageDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    getUserUsageDaily(userId, days)
      .then((rows) => {
        if (!cancelled) setData(rows);
      })
      .catch(() => {
        if (!cancelled) setError("Impossible de charger l'historique d'usage");
      });
    return () => {
      cancelled = true;
    };
  }, [userId, days]);

  if (error) {
    return <p style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>{error}</p>;
  }
  if (!data) {
    return <p style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>Chargement...</p>;
  }

  const totals = data.map((d) => d.prompt_tokens + d.completion_tokens);
  const max = Math.max(...totals, 1);
  const barWidth = 100 / data.length;
  const allZero = totals.every((t) => t === 0);

  return (
    <div>
      {allZero && (
        <p style={{ fontSize: 12, color: "var(--ink-soft)", marginBottom: 6 }}>
          Aucune activité sur cette période.
        </p>
      )}
      <svg
        viewBox={`0 0 100 ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        style={{ width: "100%", height: CHART_HEIGHT, display: "block" }}
      >
        {data.map((d, i) => {
          const total = d.prompt_tokens + d.completion_tokens;
          const h = Math.max((total / max) * (CHART_HEIGHT - 4), BAR_MIN_HEIGHT);
          const x = i * barWidth;
          return (
            <rect
              key={d.date}
              x={x + barWidth * 0.15}
              y={CHART_HEIGHT - h}
              width={barWidth * 0.7}
              height={h}
              fill="var(--accent)"
              rx="1"
            >
              <title>
                {d.date} — {total} tokens ({d.prompt_tokens} prompt / {d.completion_tokens} réponse), {d.request_count} requête(s)
              </title>
            </rect>
          );
        })}
      </svg>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 10,
          color: "var(--ink-soft)",
          marginTop: 4,
        }}
      >
        <span>{data[0].date}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Créer `frontend/components/AdminUserDetailPanel.tsx`**

```tsx
"use client";

import { AdminUser } from "../lib/api";
import { formatTokenCount, formatLastActive } from "../lib/format";
import UsageChart from "./UsageChart";

interface Props {
  user: AdminUser;
  onClose: () => void;
}

export default function AdminUserDetailPanel({ user, onClose }: Props) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card modal-card" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: 17 }}>{user.display_name}</h2>
            <p style={{ fontSize: 12.5, color: "var(--ink-soft)", margin: "2px 0 0" }}>{user.email}</p>
          </div>
          <button className="ghost" onClick={onClose} style={{ padding: "4px 10px", fontSize: 12 }}>
            Fermer
          </button>
        </div>

        <div style={{ display: "flex", gap: 20, marginBottom: 20, fontSize: 12.5 }}>
          <div>
            <div style={{ color: "var(--ink-soft)" }}>Tokens (30j)</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{formatTokenCount(user.total_tokens_30d)}</div>
          </div>
          <div>
            <div style={{ color: "var(--ink-soft)" }}>Dernière activité</div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{formatLastActive(user.last_active_at)}</div>
          </div>
        </div>

        <p
          style={{
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--ink-soft)",
            marginBottom: 8,
          }}
        >
          Consommation — 30 derniers jours
        </p>
        <UsageChart userId={user.id} days={30} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Intégrer le panneau dans `frontend/app/admin/page.tsx`**

Ajouter l'import en haut du fichier :

```tsx
import AdminUserDetailPanel from "../../components/AdminUserDetailPanel";
```

Ajouter l'état, avec les autres `useState` :

```tsx
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
```

Remplacer la cellule « Compte » du tableau :

```tsx
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <UserAvatarBadge initials={getInitials(u.display_name)} size={28} />
                    <div>
                      <div style={{ fontSize: 13.5 }}>{u.display_name}</div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-soft)" }}>{u.email}</div>
                    </div>
                  </div>
                </td>
```

par :

```tsx
                <td>
                  <button className="link-cell" onClick={() => setSelectedUser(u)}>
                    <UserAvatarBadge initials={getInitials(u.display_name)} size={28} />
                    <div>
                      <div className="link-cell-name" style={{ fontSize: 13.5 }}>
                        {u.display_name}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--ink-soft)" }}>{u.email}</div>
                    </div>
                  </button>
                </td>
```

Ajouter juste avant la fermeture de `</main>`, après le bloc `{showCreateModal && (...)}` :

```tsx
      {selectedUser && (
        <AdminUserDetailPanel user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
```

- [ ] **Step 4: Vérifier la compilation TypeScript**

Run (depuis `frontend/`) : `npx tsc --noEmit`
Expected: aucune erreur

- [ ] **Step 5: Vérifier le build**

Run (depuis `frontend/`) : `npm run build`
Expected: build réussi sans erreur

- [ ] **Step 6: Vérification manuelle dans le navigateur**

Avec le backend (`uvicorn api.main:app --port 8000`) et le frontend (`npm run dev`, port 3000) lancés, connecté avec un compte **admin** :

1. Ouvrir le menu compte → un lien « Administration » apparaît (absent pour un compte non-admin).
2. Aller sur `/admin` → tableau des comptes visible, avec tokens/dernière activité.
3. Créer un compte → bannière avec le mot de passe temporaire, nouvelle ligne dans le tableau (0 token, « Jamais »).
4. Basculer le mode DSI ou le statut actif d'un compte → mise à jour immédiate, persiste après rafraîchissement (F5).
5. Tenter de désactiver/rétrograder le dernier admin actif → message d'erreur affiché tel quel (409 de l'API), pas de changement d'état.
6. Cliquer sur le nom d'un compte → panneau de détail avec le graphique en barres ; survoler une barre → infobulle avec le détail.
7. Se connecter avec un compte non-admin et tenter `/admin` directement dans l'URL → redirection vers `/chat`.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/UsageChart.tsx frontend/components/AdminUserDetailPanel.tsx frontend/app/admin/page.tsx frontend/app/globals.css
git commit -m "feat(frontend): graphique de consommation et panneau de détail admin"
```
