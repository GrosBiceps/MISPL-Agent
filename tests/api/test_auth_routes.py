"""Tests d'intégration des routes /auth/login, /auth/logout, /auth/me."""

from api.models import User
from api.security import hash_password


def make_user(db_session_factory, **overrides):
    defaults = dict(
        email="tech@labo.fr", password_hash=hash_password("MotDePasseRobuste1!"),
        display_name="Tech Un", platform_role="user", can_use_dsi_mode=False, is_active=True,
    )
    defaults.update(overrides)
    db = db_session_factory()
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.close()


class TestLogin:
    def test_correct_credentials_sets_cookie_and_returns_user(self, client, db_session_factory):
        make_user(db_session_factory)
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "MotDePasseRobuste1!"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "tech@labo.fr"
        assert resp.json()["can_use_dsi_mode"] is False
        assert "session_token" in resp.cookies

    def test_wrong_password_returns_401(self, client, db_session_factory):
        make_user(db_session_factory)
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "faux"})
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, client, db_session_factory):
        resp = client.post("/auth/login", json={"email": "inconnu@labo.fr", "password": "peuimporte"})
        assert resp.status_code == 401

    def test_locked_account_and_wrong_password_return_same_status_and_detail(self, client, db_session_factory):
        make_user(db_session_factory)
        # Verrouille le compte : 5 mauvais mots de passe
        for _ in range(5):
            client.post("/auth/login", json={"email": "tech@labo.fr", "password": "faux"})
        locked_resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "faux"})
        unknown_resp = client.post("/auth/login", json={"email": "inconnu@labo.fr", "password": "peuimporte"})
        assert locked_resp.status_code == unknown_resp.status_code == 401
        assert locked_resp.json()["detail"] == unknown_resp.json()["detail"]

    def test_oversized_password_rejected_before_hashing(self, client, db_session_factory):
        make_user(db_session_factory)
        resp = client.post("/auth/login", json={"email": "tech@labo.fr", "password": "x" * 300})
        assert resp.status_code == 422

    def test_login_rate_limited_after_threshold_per_ip(self, client, db_session_factory):
        for _ in range(10):
            client.post("/auth/login", json={"email": "ratelimit-probe@labo.fr", "password": "whatever"})
        resp = client.post("/auth/login", json={"email": "ratelimit-probe@labo.fr", "password": "whatever"})
        assert resp.status_code == 429


class TestMe:
    def test_me_without_login_returns_401(self, client, db_session_factory):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_after_login_returns_current_user(self, client, db_session_factory):
        make_user(db_session_factory, display_name="Tech Un")
        client.post("/auth/login", json={"email": "tech@labo.fr", "password": "MotDePasseRobuste1!"})
        resp = client.get("/auth/me")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Tech Un"


class TestLogout:
    def test_logout_then_me_returns_401(self, client, db_session_factory):
        make_user(db_session_factory)
        client.post("/auth/login", json={"email": "tech@labo.fr", "password": "MotDePasseRobuste1!"})
        logout_resp = client.post("/auth/logout")
        assert logout_resp.status_code == 200
        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 401
