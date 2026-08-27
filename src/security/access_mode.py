"""
Gestion d'accès à deux modes — DSI (génération complète) / Technicien (bridé).

Défense en profondeur à deux couches :
  1. Consigne injectée dans le prompt système (le LLM doit refuser de lui-même).
  2. Barrière dure post-génération (enforce_access_mode) qui remplace la réponse
     si une boucle WHILE/REPEAT apparaît quand même — que ce soit dans un bloc
     ```mispl (réutilisant le même extracteur que le linter) ou dans le texte
     brut de la réponse (code non fenêtré, pseudo-code) dès lors qu'il a une
     saveur MISPL — jamais de confiance aveugle dans le respect du prompt par
     le LLM.

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

# Marqueurs indiquant une "saveur" MISPL dans du texte non fenêtré. Utilisé
# pour scoper la détection de boucle en texte brut et éviter de bloquer à tort
# une prose ordinaire contenant le mot anglais "while" (ex: "while this works").
_MISPL_FLAVOR_PATTERN = re.compile(
    r"\bPROGRAM\b|\bENDIF\b|\bRETURN\b|:=|\.[A-Za-z_][A-Za-z0-9_]*\b",
    re.IGNORECASE,
)


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


_FENCED_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
_LOOP_CONTEXT_WINDOW = 2  # lignes avant/après à inspecter pour la saveur MISPL


def _contains_unfenced_loop(response: str) -> bool:
    """
    Détecte une boucle WHILE/REPEAT dans le texte brut d'une réponse, en
    dehors de tout bloc ```...``` (déjà couvert par la vérification via
    extract_mispl_blocks) — par exemple du pseudo-code non fenêtré.

    Scopée par proximité : un match WHILE/REPEAT ne déclenche le refus que si
    une marque de saveur MISPL (PROGRAM, ENDIF, RETURN, `:=`, accesseur
    `.Champ`) apparaît sur la même ligne ou à quelques lignes d'écart. Cela
    évite de bloquer à tort une prose ordinaire contenant le mot anglais
    "while" loin de tout code MISPL (ex: "while this works...").
    """
    # Les blocs fenêtrés sont déjà vérifiés séparément (voir enforce_access_mode) ;
    # on les retire ici pour ne pas polluer les fenêtres de contexte avec du
    # code légitime situé après un "while" anglais dans la prose environnante.
    unfenced = _FENCED_BLOCK_PATTERN.sub("", response)

    lines = unfenced.splitlines()
    for i, line in enumerate(lines):
        if not _LOOP_PATTERN.search(line):
            continue
        window_start = max(0, i - _LOOP_CONTEXT_WINDOW)
        window_end = min(len(lines), i + _LOOP_CONTEXT_WINDOW + 1)
        window = "\n".join(lines[window_start:window_end])
        if _MISPL_FLAVOR_PATTERN.search(window):
            return True
    return False


def enforce_access_mode(response: str, mode: str) -> str:
    """
    Barrière dure : en mode Technicien, si la réponse contient WHILE/REPEAT
    malgré la consigne du prompt système, elle est remplacée par le message
    de refus — que la boucle apparaisse dans un bloc ```mispl ou dans du
    texte/pseudo-code non fenêtré ayant une saveur MISPL. Ne fait rien en
    mode DSI.
    """
    if mode != MODE_TECHNICIEN:
        return response

    # Import différé pour garder src/agent importable sans src/security (et inversement).
    from src.agent.linter import extract_mispl_blocks

    for block in extract_mispl_blocks(response):
        if _contains_loop(block):
            return REFUSAL_MESSAGE

    if _contains_unfenced_loop(response):
        return REFUSAL_MESSAGE

    return response


def access_mode_for_user(can_use_dsi_mode: bool) -> str:
    """
    Dérive le mode de génération depuis l'attribut de compte can_use_dsi_mode.

    Remplace, pour la future API de comptes, le mécanisme historique de mot
    de passe DSI partagé (verify_dsi_password ci-dessus). Ce dernier reste en
    place pour l'instant : app.py (Streamlit, toujours en production) en
    dépend encore, et sa migration est un chantier séparé.
    """
    return MODE_DSI if can_use_dsi_mode else MODE_TECHNICIEN
