"""
Gestion d'accès à deux modes — DSI (génération complète) / Technicien (bridé).

Défense en profondeur à deux couches :
  1. Consigne injectée dans le prompt système (le LLM doit refuser de lui-même).
  2. Barrière dure post-génération (enforce_access_mode) qui remplace la réponse
     si une boucle WHILE/REPEAT apparaît quand même dans un bloc ```mispl,
     réutilisant le même extracteur que le linter — jamais de confiance
     aveugle dans le respect du prompt par le LLM.

Mode par défaut : TECHNICIEN (fail-safe). Le mode DSI ne peut être atteint
qu'en fournissant le mot de passe correspondant au hash stocké en .env.
Si le hash n'est pas configuré, le déverrouillage DSI est impossible.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re

MODE_DSI = "dsi"
MODE_TECHNICIEN = "technicien"
DEFAULT_MODE = MODE_TECHNICIEN

_PBKDF2_ITERATIONS = 200_000

# Message affiché au technicien quand une demande nécessite une boucle.
REFUSAL_MESSAGE = (
    "🔒 **Génération réservée au mode DSI**\n\n"
    "Cette demande nécessite une boucle (`WHILE`/`REPEAT`), dont la génération "
    "est réservée au mode DSI pour limiter le risque de boucle infinie côté "
    "serveur GLIMS.\n\n"
    "Contactez la DSI si ce script est nécessaire."
)

# Consigne injectée dans le prompt système en mode Technicien.
TECHNICIEN_PROMPT_RESTRICTIONS = """## Restriction — Mode Technicien actif
Le mode DSI (génération complète) n'est PAS activé pour cette session.
INTERDICTION ABSOLUE de générer une boucle `WHILE` ou `REPEAT` dans le code MISPL.
Si la demande nécessite une boucle pour être satisfaite, NE GÉNÈRE AUCUN CODE et
réponds uniquement :
"🔒 Génération réservée au mode DSI — cette demande nécessite une boucle. Contactez la DSI."
"""

_LOOP_PATTERN = re.compile(r"\b(WHILE|REPEAT)\b", re.IGNORECASE)


def hash_password(password: str, salt_hex: str) -> str:
    """Dérive un hash PBKDF2-HMAC-SHA256 hex à partir du mot de passe et du sel (hex)."""
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return digest.hex()


def generate_salt() -> str:
    return os.urandom(16).hex()


def verify_dsi_password(password: str) -> bool:
    """
    Vérifie le mot de passe DSI contre le hash configuré dans l'environnement
    (MISPL_DSI_PASSWORD_HASH + MISPL_DSI_PASSWORD_SALT).

    Fail-safe : si le hash n'est pas configuré, retourne toujours False —
    le mode DSI est alors définitivement inatteignable tant que la DSI n'a
    pas exécuté scripts/set_dsi_password.py.
    """
    if not password:
        return False
    stored_hash = os.environ.get("MISPL_DSI_PASSWORD_HASH", "")
    salt_hex = os.environ.get("MISPL_DSI_PASSWORD_SALT", "")
    if not stored_hash or not salt_hex:
        return False
    try:
        candidate_hash = hash_password(password, salt_hex)
    except ValueError:
        return False
    return hmac.compare_digest(candidate_hash, stored_hash)


def build_restrictions_prompt(mode: str) -> str:
    """Bloc de consigne à ajouter au prompt système selon le mode. Vide en mode DSI."""
    if mode == MODE_TECHNICIEN:
        return TECHNICIEN_PROMPT_RESTRICTIONS
    return ""


def _contains_loop(mispl_code: str) -> bool:
    return bool(_LOOP_PATTERN.search(mispl_code))


def enforce_access_mode(response: str, mode: str) -> str:
    """
    Barrière dure : en mode Technicien, si un bloc ```mispl contient WHILE/REPEAT
    malgré la consigne du prompt système, la réponse entière est remplacée par
    le message de refus. Ne fait rien en mode DSI.
    """
    if mode != MODE_TECHNICIEN:
        return response

    # Import différé pour garder src/agent importable sans src/security (et inversement).
    from src.agent.linter import extract_mispl_blocks

    for block in extract_mispl_blocks(response):
        if _contains_loop(block):
            return REFUSAL_MESSAGE

    return response
