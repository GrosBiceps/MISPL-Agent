"""Vérifie que l'API autorise le frontend Next.js en local (CORS + credentials)."""


class TestCORS:
    def test_allows_configured_frontend_origin_with_credentials(self, client, db_session_factory):
        resp = client.get("/auth/me", headers={"Origin": "http://localhost:3000"})
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert resp.headers.get("access-control-allow-credentials") == "true"
