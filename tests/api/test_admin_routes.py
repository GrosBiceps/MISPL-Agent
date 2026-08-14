"""Tests d'intégration des routes /admin/users."""

from api.models import User
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
