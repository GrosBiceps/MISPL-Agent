"""Clé API OpenRouter de l'interface Streamlit.

La clé du serveur (OPENROUTER_API_KEY, .env) ne doit jamais quitter le
serveur : elle n'est ni pré-remplie dans un widget (dont la valeur est
envoyée au navigateur), ni affichée. Un utilisateur peut saisir sa propre
clé ; à défaut, la clé du serveur est utilisée côté serveur.
"""

from __future__ import annotations

import os


def server_key_configured() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def effective_api_key(session_key: str | None) -> str:
    """Clé saisie par l'utilisateur si présente, sinon clé du serveur."""
    if session_key and session_key.strip():
        return session_key.strip()
    return os.environ.get("OPENROUTER_API_KEY", "").strip()
