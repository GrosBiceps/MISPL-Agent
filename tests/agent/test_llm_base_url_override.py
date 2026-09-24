"""Tests de la surcharge MISPL_LLM_BASE_URL (mispl_agent.OPENROUTER_BASE_URL).

La surcharge sert uniquement aux tests locaux (banc scripts/claude_harness/,
serveur OpenAI-compatible factice sur 127.0.0.1). Sans la variable, l'URL
OpenRouter par défaut doit rester strictement inchangée.

Le module est chargé dans une copie isolée (nom de module distinct) pour ne
jamais altérer le module réel src.agent.mispl_agent partagé par les autres
tests.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

AGENT_PATH = ROOT / "src" / "agent" / "mispl_agent.py"
DEFAULT_URL = "https://openrouter.ai/api/v1"


def _load_isolated_agent_module():
    spec = importlib.util.spec_from_file_location("_mispl_agent_base_url_test", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLlmBaseUrlOverride:
    def test_default_is_openrouter_when_env_absent(self, monkeypatch):
        monkeypatch.delenv("MISPL_LLM_BASE_URL", raising=False)
        module = _load_isolated_agent_module()
        assert module.OPENROUTER_BASE_URL == DEFAULT_URL

    def test_env_overrides_base_url(self, monkeypatch):
        monkeypatch.setenv("MISPL_LLM_BASE_URL", "http://127.0.0.1:59999/v1")
        module = _load_isolated_agent_module()
        assert module.OPENROUTER_BASE_URL == "http://127.0.0.1:59999/v1"

    def test_client_uses_overridden_base_url(self, monkeypatch):
        # La construction du client OpenAI n'émet aucune requête réseau.
        monkeypatch.setenv("MISPL_LLM_BASE_URL", "http://127.0.0.1:59999/v1")
        module = _load_isolated_agent_module()
        client = module._get_client("sk-test-local")
        assert str(client.base_url).rstrip("/") == "http://127.0.0.1:59999/v1"

    def test_client_uses_openrouter_by_default(self, monkeypatch):
        monkeypatch.delenv("MISPL_LLM_BASE_URL", raising=False)
        module = _load_isolated_agent_module()
        client = module._get_client("sk-test-local")
        assert str(client.base_url).rstrip("/") == DEFAULT_URL

    def test_client_refuses_unlisted_third_party_host(self, monkeypatch):
        """Audit sécurité 2026-09-24 : une surcharge vers un hôte tiers non
        autorisé fait échouer la création du client (fail-closed), au lieu d'y
        envoyer les questions et la clé API."""
        import pytest

        monkeypatch.setenv("MISPL_LLM_BASE_URL", "https://llm.exemple-tiers.com/v1")
        monkeypatch.delenv("MISPL_LLM_ALLOWED_HOSTS", raising=False)
        module = _load_isolated_agent_module()
        with pytest.raises(ValueError):
            module._get_client("sk-test-local")
