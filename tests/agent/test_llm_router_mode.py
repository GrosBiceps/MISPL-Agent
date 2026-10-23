"""Tests du mode routeur (MISPL_LLM_MODEL, ex. FreeLLMAPI local).

- le routeur est appelé en premier, avec sa clé propre (MISPL_LLM_API_KEY) ;
- le modèle réellement servi (en-tête X-Routed-Via) est remonté ;
- routeur en panne → repli sur OpenRouter direct (URL OpenRouter, pas celle
  du routeur), la clé OpenRouter n'étant jamais envoyée au routeur ;
- sans MISPL_LLM_MODEL, comportement historique inchangé.

Module chargé dans une copie isolée pour ne pas altérer src.agent.mispl_agent.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

AGENT_PATH = ROOT / "src" / "agent" / "mispl_agent.py"
ROUTER_URL = "http://127.0.0.1:3001/v1"


def _load(monkeypatch, router_model: str | None):
    monkeypatch.setenv("MISPL_LLM_BASE_URL", ROUTER_URL)
    monkeypatch.setenv("MISPL_LLM_API_KEY", "freellmapi-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    if router_model:
        monkeypatch.setenv("MISPL_LLM_MODEL", router_model)
    else:
        monkeypatch.delenv("MISPL_LLM_MODEL", raising=False)
    spec = importlib.util.spec_from_file_location("_mispl_agent_router_test", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_router(headers=None, error=None):
    raw = MagicMock()
    raw.headers = headers or {}
    raw.parse.return_value = MagicMock(model="auto:smart")
    client = MagicMock()
    create = client.chat.completions.with_raw_response.create
    if error:
        create.side_effect = error
    else:
        create.return_value = raw
    return client


class TestRouterMode:
    def test_router_used_first_with_routed_model(self, monkeypatch):
        mod = _load(monkeypatch, "auto:smart")
        router = _fake_router(headers={"x-routed-via": "groq/llama-4-maverick"})
        monkeypatch.setattr(mod, "_get_router_client", lambda: router)
        direct = MagicMock(side_effect=AssertionError("OpenRouter direct ne doit pas être appelé"))
        monkeypatch.setattr(mod, "_call_with_fallback", direct)

        used, _, via_router = mod._call_llm(None, mod.DEFAULT_MODEL, [])

        assert used == "router:groq/llama-4-maverick"
        assert via_router is True
        kwargs = router.chat.completions.with_raw_response.create.call_args.kwargs
        assert kwargs["model"] == "auto:smart"

    def test_router_down_falls_back_to_openrouter_direct(self, monkeypatch):
        mod = _load(monkeypatch, "auto:smart")
        monkeypatch.setattr(mod, "_get_router_client", lambda: _fake_router(error=ConnectionError("refused")))
        captured = {}

        def _direct(client, model, messages, stream=False):
            captured["base_url"] = str(client.base_url)
            captured["api_key"] = client.api_key
            return model, MagicMock()

        monkeypatch.setattr(mod, "_call_with_fallback", _direct)

        used, _, via_router = mod._call_llm(None, mod.DEFAULT_MODEL, [])

        assert via_router is False
        assert used == mod.DEFAULT_MODEL
        assert captured["base_url"].startswith("https://openrouter.ai/api/v1")
        assert captured["api_key"] == "sk-or-test"

    def test_router_client_uses_router_key_only(self, monkeypatch):
        mod = _load(monkeypatch, "auto:smart")
        client = mod._get_router_client()
        assert client.api_key == "freellmapi-test"
        assert str(client.base_url).startswith(ROUTER_URL)

    def test_without_router_model_base_url_keeps_legacy_meaning(self, monkeypatch):
        mod = _load(monkeypatch, None)
        assert mod.LLM_ROUTER_MODEL == ""
        client = mod._get_client("sk-or-test")
        assert str(client.base_url).startswith(ROUTER_URL)
