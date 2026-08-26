"""Tests du middleware global de limitation de la taille du corps de requête."""

import api.main as main


class TestRequestBodySizeLimit:
    def test_oversized_body_rejected_with_413(self, client):
        huge_password = "x" * (main.MAX_REQUEST_BODY_BYTES + 1)
        resp = client.post("/auth/login", json={"email": "a@labo.fr", "password": huge_password})
        assert resp.status_code == 413

    def test_body_within_limit_is_not_rejected_by_middleware(self, client, db_session_factory):
        # Un corps normal (bien en dessous de la limite) doit atteindre la
        # route et être traité normalement (ici : identifiants invalides ->
        # 401, pas 413 -> preuve que le middleware n'a pas bloqué la requête).
        resp = client.post("/auth/login", json={"email": "a@labo.fr", "password": "whatever"})
        assert resp.status_code == 401
