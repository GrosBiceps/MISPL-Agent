"""
Tests du fallback/retry OpenRouter de mispl_agent.

Vérifie le correctif de l'audit sécurité/fiabilité sur _call_with_fallback :
1. Un budget de temps total borne l'attente cumulée sur tous les modèles/
   tentatives, pour éviter qu'un worker FastAPI (thread synchrone) reste
   bloqué plusieurs minutes si tous les modèles gratuits sont rate-limités.
2. Toute erreur générique est loguée à chaque tentative (pas seulement à la
   toute fin), pour ne pas masquer un échec systémique (ex: clé API invalide).
"""

import logging
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from openai import RateLimitError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import src.agent.mispl_agent as agent_mod


def _make_rate_limit_error(retry_after_seconds=20):
    return RateLimitError(
        message="rate limited",
        response=MagicMock(status_code=429, headers={}),
        body={"error": {"metadata": {"retry_after_seconds": retry_after_seconds}}},
    )


class TestCallWithFallbackDeadline:
    def test_deadline_caps_total_wait_time(self, monkeypatch):
        """Tous les modèles rate-limités : le temps total d'attente ne doit
        jamais dépasser le budget configuré, même avec 6 modèles x 2 tentatives."""
        monkeypatch.setattr(agent_mod, "_MAX_TOTAL_WAIT_SECONDS", 2)

        def _raise_rate_limit(*args, **kwargs):
            raise _make_rate_limit_error(retry_after_seconds=20)

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = _raise_rate_limit

        start = time.monotonic()
        with pytest.raises(RateLimitError):
            agent_mod._call_with_fallback(fake_client, agent_mod.FALLBACK_ORDER[0], messages=[])
        elapsed = time.monotonic() - start

        # Le budget est de 2s ; même avec retry_after=20s annoncé par l'API,
        # le temps réel écoulé doit rester proche du budget (marge généreuse
        # pour la latence de test), jamais des dizaines de secondes.
        assert elapsed < 10

    def test_generic_exception_logged_for_every_model(self, monkeypatch, caplog):
        """Une erreur générique (ex: clé API invalide) doit être loguée à
        chaque tentative, pas seulement re-levée silencieusement à la fin."""
        monkeypatch.setattr(agent_mod, "_MAX_TOTAL_WAIT_SECONDS", 5)

        def _raise_generic(*args, **kwargs):
            raise RuntimeError("invalid api key")

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = _raise_generic

        with caplog.at_level(logging.WARNING):
            with pytest.raises(RuntimeError):
                agent_mod._call_with_fallback(
                    fake_client, agent_mod.FALLBACK_ORDER[0], messages=[], max_retries=1
                )

        warning_messages = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("invalid api key" in m for m in warning_messages)

    def test_rate_limit_retries_same_model_before_falling_back(self, monkeypatch):
        """Régression : sur un 429, le code doit retenter le MÊME modèle
        (max_retries - 1 fois) avant de basculer sur le fallback suivant —
        pas basculer immédiatement après le premier sommeil (bug trouvé lors
        de l'audit du 2026-08-26 : un `break` inconditionnel empêchait toute
        deuxième tentative sur le modèle courant)."""
        monkeypatch.setattr(agent_mod, "_MAX_TOTAL_WAIT_SECONDS", 5)
        monkeypatch.setattr(time, "sleep", lambda *_a, **_kw: None)

        calls = []
        fake_completion = MagicMock()

        def _side_effect(*args, **kwargs):
            calls.append(kwargs["model"])
            if len(calls) == 1:
                raise _make_rate_limit_error(retry_after_seconds=1)
            return fake_completion

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = _side_effect

        used_model, completion = agent_mod._call_with_fallback(
            fake_client, agent_mod.FALLBACK_ORDER[0], messages=[], max_retries=2
        )

        assert calls == [agent_mod.FALLBACK_ORDER[0], agent_mod.FALLBACK_ORDER[0]]
        assert used_model == agent_mod.FALLBACK_ORDER[0]
        assert completion is fake_completion

    def test_success_returns_model_and_completion(self, monkeypatch):
        fake_completion = MagicMock()
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_completion

        used_model, completion = agent_mod._call_with_fallback(
            fake_client, agent_mod.FALLBACK_ORDER[0], messages=[]
        )
        assert used_model == agent_mod.FALLBACK_ORDER[0]
        assert completion is fake_completion
