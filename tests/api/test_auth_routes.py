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

    def test_login_rate_limited_by_ip_after_many_different_emails(self, client, db_session_factory):
        """Un attaquant faisant tourner 30+ emails différents depuis la même IP
        doit finir par être bloqué, même si aucun email individuel n'atteint
        la limite par-compte — c'est exactement le credential-stuffing que la
        limite (IP, email) seule ne détectait pas."""
        for i in range(30):
            client.post("/auth/login", json={"email": f"probe-{i}@labo.fr", "password": "whatever"})
        resp = client.post("/auth/login", json={"email": "probe-final@labo.fr", "password": "whatever"})
        assert resp.status_code == 429


class TestLoginRateLimiterCleanup:
    def test_abandoned_keys_are_purged_from_memory(self, client, db_session_factory, monkeypatch):
        """`_login_attempts`/`_login_attempts_by_ip` sont des dicts module-level
        qui vivent pour toute la durée du process. Une clé (IP, email) touchée
        une seule fois puis jamais revisitée ne doit pas rester indéfiniment en
        mémoire une fois sa fenêtre de rate limiting expirée."""
        import time
        import api.routers.auth as auth_router

        client.post("/auth/login", json={"email": "abandoned@labo.fr", "password": "x"})
        assert any("abandoned@labo.fr" in k for k in auth_router._login_attempts)

        future = time.monotonic() + auth_router._LOGIN_RATE_WINDOW_SECONDS + 1
        monkeypatch.setattr(auth_router.time, "monotonic", lambda: future)

        # Une tentative sans rapport, une fois la fenêtre expirée, déclenche le
        # nettoyage — la clé abandonnée doit disparaître du dict, pas juste
        # voir sa liste de timestamps vidée silencieusement.
        client.post("/auth/login", json={"email": "other@labo.fr", "password": "x"})

        assert not any("abandoned@labo.fr" in k for k in auth_router._login_attempts)


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
