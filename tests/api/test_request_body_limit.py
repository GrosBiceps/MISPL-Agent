"""Tests du middleware global de limitation de la taille du corps de requête."""

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

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

    def test_oversized_body_rejected_even_without_content_length(self):
        """Régression (revue du 2026-08-27) : le contrôle initial ne lisait
        que l'en-tête Content-Length, absent pour un corps en
        Transfer-Encoding: chunked — un client pouvait ainsi faire passer un
        corps volumineux sans déclencher le 413. Le flux réel doit être borné
        indépendamment de tout en-tête déclaré par le client."""
        chunk = b"x" * 1024
        n_chunks = (main.MAX_REQUEST_BODY_BYTES // len(chunk)) + 10
        sent = {"count": 0}

        async def receive():
            if sent["count"] < n_chunks:
                sent["count"] += 1
                return {"type": "http.request", "body": chunk, "more_body": sent["count"] < n_chunks}
            return {"type": "http.request", "body": b"", "more_body": False}

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/auth/login",
            "headers": [],  # pas de content-length, comme un corps chunked
            "query_string": b"",
        }
        request = Request(scope, receive=receive)

        async def call_next(_request):
            await _request.body()  # force la consommation complète du flux
            return None

        async def run():
            await main.limit_request_body_size(request, call_next)

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(run())
        assert exc_info.value.status_code == 413
