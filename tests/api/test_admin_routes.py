"""Tests d'intégration des routes /admin/users."""

import datetime

from api.models import UsageDaily, User
from api.security import hash_password


def make_admin(db_session_factory, email="admin@labo.fr"):
    db = db_session_factory()
    user = User(
        email=email, password_hash=hash_password("AdminMdp1!"),
        display_name="Admin", platform_role="admin", can_use_dsi_mode=True, is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()


def make_regular_user(db_session_factory, email="tech@labo.fr"):
    db = db_session_factory()
    user = User(
        email=email, password_hash=hash_password("TechMdp1!"),
        display_name="Tech", platform_role="user", can_use_dsi_mode=False, is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()
    return user


def login_as(client, email, password):
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp


class TestCreateUser:
    def test_admin_can_create_user(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post("/admin/users", json={
            "email": "nouveau@labo.fr", "display_name": "Nouveau Tech",
            "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "nouveau@labo.fr"
        assert "temporary_password" in body
        assert len(body["temporary_password"]) >= 12

    def test_non_admin_cannot_create_user(self, client, db_session_factory):
        make_regular_user(db_session_factory)
        login_as(client, "tech@labo.fr", "TechMdp1!")
        resp = client.post("/admin/users", json={
            "email": "x@labo.fr", "display_name": "X", "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_user(self, client, db_session_factory):
        resp = client.post("/admin/users", json={
            "email": "x@labo.fr", "display_name": "X", "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 401

    def test_duplicate_email_rejected(self, client, db_session_factory):
        make_admin(db_session_factory)
        make_regular_user(db_session_factory, email="existe@labo.fr")
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post("/admin/users", json={
            "email": "existe@labo.fr", "display_name": "X", "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 409

    def test_duplicate_email_rejected_case_insensitive_and_login_case_insensitive(
        self, client, db_session_factory
    ):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.post("/admin/users", json={
            "email": "nouveau.tech@labo.fr", "display_name": "Nouveau Tech",
            "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 201
        temp_password = resp.json()["temporary_password"]

        # Même email, casse différente -> rejeté (409), pas un doublon accepté.
        resp = client.post("/admin/users", json={
            "email": "Nouveau.Tech@Labo.FR", "display_name": "Doublon",
            "platform_role": "user", "can_use_dsi_mode": False,
        })
        assert resp.status_code == 409

        # Login avec une casse différente de celle utilisée à la création réussit.
        client.post("/auth/logout")
        resp = client.post("/auth/login", json={
            "email": "Nouveau.Tech@Labo.FR", "password": temp_password,
        })
        assert resp.status_code == 200


class TestListUsers:
    def test_admin_can_list_users(self, client, db_session_factory):
        make_admin(db_session_factory)
        make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.get("/admin/users")
        assert resp.status_code == 200
        emails = {u["email"] for u in resp.json()}
        assert {"admin@labo.fr", "tech@labo.fr"} <= emails


class TestUpdateUser:
    def test_admin_can_toggle_dsi_mode(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.patch(f"/admin/users/{user.id}", json={"can_use_dsi_mode": True})
        assert resp.status_code == 200
        assert resp.json()["can_use_dsi_mode"] is True

    def test_cannot_demote_last_active_admin(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin = db.query(User).filter(User.email == "admin@labo.fr").one()
        admin_id = admin.id
        db.close()
        resp = client.patch(f"/admin/users/{admin_id}", json={"platform_role": "user"})
        assert resp.status_code == 409

    def test_cannot_deactivate_last_active_admin(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin = db.query(User).filter(User.email == "admin@labo.fr").one()
        admin_id = admin.id
        db.close()
        resp = client.patch(f"/admin/users/{admin_id}", json={"is_active": False})
        assert resp.status_code == 409

    def test_invalid_platform_role_on_last_admin_returns_422_not_409(self, client, db_session_factory):
        make_admin(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin = db.query(User).filter(User.email == "admin@labo.fr").one()
        admin_id = admin.id
        db.close()
        resp = client.patch(f"/admin/users/{admin_id}", json={"platform_role": "superadmin"})
        assert resp.status_code == 422

    def test_can_demote_admin_when_another_active_admin_remains(self, client, db_session_factory):
        make_admin(db_session_factory, email="admin@labo.fr")
        make_admin(db_session_factory, email="admin2@labo.fr")
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin2 = db.query(User).filter(User.email == "admin2@labo.fr").one()
        admin2_id = admin2.id
        db.close()
        resp = client.patch(f"/admin/users/{admin2_id}", json={"platform_role": "user"})
        assert resp.status_code == 200
        assert resp.json()["platform_role"] == "user"

    def test_can_deactivate_admin_when_another_active_admin_remains(self, client, db_session_factory):
        make_admin(db_session_factory, email="admin@labo.fr")
        make_admin(db_session_factory, email="admin2@labo.fr")
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        db = db_session_factory()
        admin2 = db.query(User).filter(User.email == "admin2@labo.fr").one()
        admin2_id = admin2.id
        db.close()
        resp = client.patch(f"/admin/users/{admin2_id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


class TestResetPassword:
    def test_reset_generates_new_temp_password(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post(f"/admin/users/{user.id}/reset-password")
        assert resp.status_code == 200
        assert len(resp.json()["temporary_password"]) >= 12

    def test_old_password_rejected_after_reset(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        login_as(client, "admin@labo.fr", "AdminMdp1!")
        client.post(f"/admin/users/{user.id}/reset-password")
        client.post("/auth/logout")
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "TechMdp1!"})
        assert resp.status_code == 401

    def test_reset_password_revokes_existing_sessions(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)

        # Le technicien a une session active dans un client séparé.
        from fastapi.testclient import TestClient
        from api.main import app
        tech_client = TestClient(app)
        login_as(tech_client, "tech@labo.fr", "TechMdp1!")
        assert tech_client.get("/auth/me").status_code == 200

        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post(f"/admin/users/{user.id}/reset-password")
        assert resp.status_code == 200

        # L'ancienne session ne fonctionne plus après le reset.
        assert tech_client.get("/auth/me").status_code == 401


class TestRevokeSessions:
    def test_revoke_kills_active_session_immediately(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)

        # Le technicien se connecte dans un client séparé pour garder sa propre session
        from fastapi.testclient import TestClient
        from api.main import app
        tech_client = TestClient(app)
        login_as(tech_client, "tech@labo.fr", "TechMdp1!")
        assert tech_client.get("/auth/me").status_code == 200

        login_as(client, "admin@labo.fr", "AdminMdp1!")
        resp = client.post(f"/admin/users/{user.id}/revoke-sessions")
        assert resp.status_code == 200
        assert resp.json()["revoked"] == 1

        assert tech_client.get("/auth/me").status_code == 401


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
        # total_tokens_30d reste correctement fenêtré...
        assert tech["total_tokens_30d"] == 0
        # ...mais last_active_at n'est PAS limité à la fenêtre de 30 jours :
        # il reflète la dernière activité réelle, quelle que soit son ancienneté.
        assert tech["last_active_at"] == old_date.isoformat()

    def test_usage_exactly_29_days_ago_included(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        boundary_date = datetime.date.today() - datetime.timedelta(days=29)
        add_usage(db_session_factory, user.id, boundary_date, prompt_tokens=40, completion_tokens=10)
        login_as(client, "admin@labo.fr", "AdminMdp1!")

        resp = client.get("/admin/users")
        tech = next(u for u in resp.json() if u["email"] == "tech@labo.fr")
        assert tech["total_tokens_30d"] == 50

    def test_usage_exactly_30_days_ago_excluded(self, client, db_session_factory):
        make_admin(db_session_factory)
        user = make_regular_user(db_session_factory)
        boundary_date = datetime.date.today() - datetime.timedelta(days=30)
        add_usage(db_session_factory, user.id, boundary_date, prompt_tokens=40, completion_tokens=10)
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
