"""Cadrage de la surcharge MISPL_LLM_BASE_URL (destination des questions).

Chaque question envoyée au LLM (avec le contexte labo et l'historique de
conversation) part vers l'URL de base configurée. Une surcharge mal saisie ou
malveillante redirigerait ces données, et la clé API, vers un serveur tiers.
Règles (fail-closed : une URL refusée fait échouer l'appel, sans repli
silencieux vers une autre destination) :

- OpenRouter en HTTPS (valeur par défaut) : autorisé ;
- boucle locale (127.0.0.0/8, ::1, localhost) en HTTP ou HTTPS : autorisé
  (banc de test scripts/claude_harness/, LLM local Ollama/vLLM sur l'hôte) ;
- tout autre hôte : HTTPS obligatoire ET hôte listé explicitement dans
  MISPL_LLM_ALLOWED_HOSTS (liste séparée par des virgules, ex. un serveur
  d'inférence interne validé par le RSSI) ;
- aucun identifiant dans l'URL (user:pass@hôte), schéma http/https seulement.
"""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

DEFAULT_LLM_BASE_URL = "https://openrouter.ai/api/v1"
_BUILTIN_ALLOWED_HTTPS_HOSTS = frozenset({"openrouter.ai"})


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _configured_allowed_hosts() -> set[str]:
    raw = os.environ.get("MISPL_LLM_ALLOWED_HOSTS", "")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def validate_llm_base_url(url: str, allowed_hosts: set[str] | None = None) -> str:
    """Retourne l'URL si elle est autorisée, lève ValueError sinon."""
    if allowed_hosts is None:
        allowed_hosts = _configured_allowed_hosts()
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if scheme not in ("http", "https") or not host:
        raise ValueError("MISPL_LLM_BASE_URL invalide : schéma http(s) et hôte requis")
    if parts.username or parts.password:
        raise ValueError("MISPL_LLM_BASE_URL ne doit pas contenir d'identifiants")
    if _is_loopback(host):
        return url.strip()
    if scheme != "https":
        raise ValueError("MISPL_LLM_BASE_URL : HTTPS obligatoire hors boucle locale")
    if host in _BUILTIN_ALLOWED_HTTPS_HOSTS or host in allowed_hosts:
        return url.strip()
    raise ValueError(
        "MISPL_LLM_BASE_URL : hôte non autorisé. Ajoutez-le à MISPL_LLM_ALLOWED_HOSTS "
        "après validation (les questions et la clé API y seraient envoyées)."
    )
