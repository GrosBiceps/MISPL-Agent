"""Tests du middleware global d'en-têtes de sécurité HTTP (WEB-01)."""


class TestSecurityHeaders:
    def test_headers_present_regardless_of_status_code(self, client):
        # /auth/me sans authentification -> 401, mais les en-têtes de
        # sécurité doivent être présents indépendamment du code de statut.
        resp = client.get("/auth/me")
        assert resp.status_code == 401
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert resp.headers["content-security-policy"] == "default-src 'none'"

    def test_docs_route_exempted_from_csp_but_keeps_other_headers(self, client):
        # /docs sert le HTML/JS de Swagger UI (chargé depuis un CDN externe) :
        # il ne peut pas recevoir le CSP strict "default-src 'none'" du reste
        # de l'API sans casser le rendu. Les autres en-têtes durcissants
        # restent appliqués.
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "content-security-policy" not in resp.headers
