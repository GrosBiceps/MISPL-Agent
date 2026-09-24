"""Garde-fous d'hygiène du dépôt et du déploiement (audit sécurité 2026-09-24) :
image Docker sans secret ni donnée, clé OpenRouter jamais envoyée au
navigateur par Streamlit, destination LLM cadrée."""

import ast
import fnmatch
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.security.llm_endpoint import DEFAULT_LLM_BASE_URL, validate_llm_base_url  # noqa: E402
from src.security.openrouter_key import effective_api_key, server_key_configured  # noqa: E402


class TestDockerignore:
    REQUIRED = [".env", "data/", "outputs/", "DSI/", "docs/audit_PI_*/", ".git/", "*.db"]

    def test_dockerignore_exists_and_excludes_sensitive_paths(self):
        lines = {
            line.strip() for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        missing = [p for p in self.REQUIRED if p not in lines]
        assert not missing, f"Motifs absents de .dockerignore : {missing}"

    def test_runtime_skills_not_excluded(self):
        # .claude/skills et .claude/rules sont lus par le prompt système.
        lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        assert ".claude/" not in [line.strip() for line in lines]


def _tracked_files() -> list[str]:
    try:
        return subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        pytest.skip("git indisponible")


def _matching(files: list[str], patterns: list[str]) -> list[str]:
    return [
        f for f in files
        if any(fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(Path(f).name, pat) for pat in patterns)
    ]


class TestGitTrackedFiles:
    FORBIDDEN = [".env", "*.db", "*.db-journal", "*.db-wal", "*.sqlite3", "docs/audit_PI_*"]

    def test_no_secret_or_database_tracked(self):
        offenders = _matching(_tracked_files(), self.FORBIDDEN)
        assert not offenders, offenders

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Constat d'audit 2026-09-24 (ÉLEVÉ, à arbitrer) : deux notes de DSI/ sont suivies par git "
            "et publiées, contrairement à CLAUDE.md. Une fois retirées de l'index "
            "(git rm --cached), ce test passera : supprimer alors ce marqueur xfail."
        ),
    )
    def test_dsi_notes_not_tracked(self):
        offenders = _matching(_tracked_files(), ["DSI/*"])
        assert not offenders, offenders


class TestStreamlitApiKeyNotSentToBrowser:
    def test_key_widget_never_prefilled(self):
        """La valeur d'un st.text_input est envoyée au navigateur même en
        type="password" : le champ de clé API doit démarrer vide."""
        tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
        found = False
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "text_input"):
                continue
            label = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else ""
            if "API" not in str(label):
                continue
            found = True
            value = next((kw.value for kw in node.keywords if kw.arg == "value"), None)
            assert value is None or (isinstance(value, ast.Constant) and value.value == ""), \
                "Le champ de clé API ne doit pas être pré-rempli"
        assert found

    def test_effective_key_prefers_user_then_server(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "cle-serveur-factice")
        assert effective_api_key("  cle-perso  ") == "cle-perso"
        assert effective_api_key("") == "cle-serveur-factice"
        assert effective_api_key(None) == "cle-serveur-factice"
        assert server_key_configured() is True
        monkeypatch.delenv("OPENROUTER_API_KEY")
        assert server_key_configured() is False
        assert effective_api_key("") == ""


class TestLlmEndpoint:
    @pytest.mark.parametrize("url", [
        DEFAULT_LLM_BASE_URL,
        "http://127.0.0.1:59999/v1",
        "http://localhost:11434/v1",
        "http://[::1]:8000/v1",
    ])
    def test_allowed(self, url):
        assert validate_llm_base_url(url, allowed_hosts=set()) == url

    @pytest.mark.parametrize("url", [
        "https://llm.exemple-tiers.com/v1",       # hôte non listé
        "http://openrouter.ai/api/v1",            # HTTP hors boucle locale
        "http://10.0.0.5:8000/v1",                # réseau interne en clair
        "https://user:pass@openrouter.ai/api/v1",  # identifiants dans l'URL
        "file:///etc/passwd",
        "not a url",
    ])
    def test_refused(self, url):
        with pytest.raises(ValueError):
            validate_llm_base_url(url, allowed_hosts=set())

    def test_explicit_allowlist(self, monkeypatch):
        monkeypatch.setenv("MISPL_LLM_ALLOWED_HOSTS", "inference.interne.example, autre.example")
        assert validate_llm_base_url("https://inference.interne.example/v1")
        with pytest.raises(ValueError):
            validate_llm_base_url("http://inference.interne.example/v1")
