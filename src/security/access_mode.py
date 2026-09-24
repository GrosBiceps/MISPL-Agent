"""
Gestion d'accès à deux modes — DSI (génération complète) / Technicien (bridé).

Défense en profondeur à deux couches :
  1. Consigne injectée dans le prompt système (le LLM doit refuser de lui-même).
  2. Barrière dure post-génération (enforce_access_mode) qui remplace la réponse
     si une boucle WHILE/REPEAT apparaît quand même — que ce soit dans un bloc
     effectivement extrait par le linter (```mispl, ou ``` générique contenant
     PROGRAM) ou n'importe où ailleurs dans la réponse (fence générique non
     reconnue par le linter, pseudo-code non fenêtré, etc.), dès lors qu'il a
     une saveur MISPL à proximité — jamais de confiance aveugle dans le
     respect du prompt par le LLM, et surtout pas dans l'hypothèse qu'« être
     dans une fence ``` » suffirait à garantir qu'un bloc a été vérifié.

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
INTERDICTION ABSOLUE de générer une boucle dans le code MISPL.
1. Une demande SANS boucle (tester une analyse, lire une valeur, formater, remplacer...) se
   traite normalement, au format habituel : ce mode ne bride QUE les boucles.
2. Si l'utilisateur parle de boucle, cherche d'abord une fonction intégrée qui rend la boucle
   inutile (ex. Replace, Lpad, Index, NumEntries, IsRequested, Attribute("...List")). Si elle
   couvre le besoin, réponds normalement avec ce code sans boucle.
3. Sinon, n'écris AUCUN bloc de code et réponds exactement :
## Contexte GLIMS
🔒 Génération réservée au mode DSI — cette demande nécessite une boucle. Contactez la DSI.
   Tu peux ajouter une phrase proposant une alternative sans boucle, sans code.
4. N'écris JAMAIS les mots-clés WHILE, REPEAT, DONE ou UNTIL dans ta réponse, ni dans le
   code, ni dans les commentaires, ni dans les notes : écris « boucle ». Une barrière
   automatique remplace par un refus toute réponse qui contient une boucle.
"""

_LOOP_PATTERN = re.compile(r"\b(WHILE|REPEAT)\b", re.IGNORECASE)

# Marqueurs indiquant une "saveur" MISPL dans du texte non fenêtré. Utilisé
# pour scoper la détection de boucle en texte brut et éviter de bloquer à tort
# une prose ordinaire contenant le mot anglais "while" (ex: "while this works").
#
# L'accesseur `.Champ` n'est PAS sous re.IGNORECASE (voir plus bas) : matché
# case-sensitive sur `.MotMajuscule`, comme le pattern nom titré de
# src/security/dlp.py pour le même type de faux positif. Sous IGNORECASE, ce
# bras matchait n'importe quel point suivi d'un mot — y compris les extensions
# de fichier dans les citations `## Source` obligatoires du format de réponse
# (CLAUDE.md), ex. "Source : function_string.htm" — bloquant à tort un refus
# légitime en mode Technicien qui cite sa source en prose.
# RETURN a été retiré des marqueurs : trop fréquent en prose ordinaire
# (française ou anglaise) parlant de code, pas spécifique aux boucles. DONE et
# UNTIL ont été ajoutés : signaux forts et spécifiques aux boucles WHILE/REPEAT,
# présents dans tous les payloads de contournement déjà couverts par les tests.
_MISPL_FLAVOR_PATTERN = re.compile(
    r"\bPROGRAM\b|\bENDIF\b|\bDONE\b|\bUNTIL\b|:="
    r"|(?-i:\.[A-Z][A-Za-z0-9_]*\b)",
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


_FENCED_BLOCK_PATTERN = re.compile(r"```(?:mispl)?\s*([\s\S]*?)```", re.IGNORECASE)
_LOOP_CONTEXT_WINDOW = 2  # lignes avant/après à inspecter pour la saveur MISPL
_WHILE_DO_PATTERN = re.compile(r"\bWHILE\b.*\bDO\b", re.IGNORECASE)
_DONE_PATTERN = re.compile(r"\bDONE\b", re.IGNORECASE)
_UNTIL_PATTERN = re.compile(r"\bUNTIL\b", re.IGNORECASE)
# Mot-clé de boucle en tête de ligne (indentation, puce ou numéro tolérés).
_STATEMENT_LOOP_PATTERN = re.compile(r"^\s*(?:[-*>]\s+|\d+[.)]\s+)?`?(WHILE|REPEAT)\b", re.IGNORECASE)


def _contains_unfenced_loop(response: str, already_checked_blocks: list[str]) -> bool:
    """
    Détecte une boucle WHILE/REPEAT dans le texte de la réponse qui n'a PAS
    déjà été inspecté par la vérification par bloc (extract_mispl_blocks).

    Important : un bloc ```...``` fenêtré n'est « déjà couvert » que s'il a
    effectivement été extrait et inspecté par extract_mispl_blocks (blocs
    ```mispl, ou blocs génériques ``` contenant PROGRAM). Un bloc ``` sans
    tag `mispl` et sans le mot `PROGRAM` (ex: pseudo-code brut dans une
    fence générique) n'est PAS extrait par extract_mispl_blocks — il ne faut
    donc pas le retirer aveuglément ici, sous peine de le rendre invisible
    aux deux couches de vérification. On ne retire du texte scanné que les
    fences dont le contenu correspond exactement à un bloc réellement
    vérifié par le for-loop de enforce_access_mode.

    Scopée par proximité : un match WHILE/REPEAT ne déclenche le refus que si
    une marque de saveur MISPL (PROGRAM, ENDIF, RETURN, `:=`, accesseur
    `.Champ`) apparaît sur la même ligne ou à quelques lignes d'écart. Cela
    évite de bloquer à tort une prose ordinaire contenant le mot anglais
    "while" loin de tout code MISPL (ex: "while this works...").

    Depuis le banc temps réel du 2026-09-24, la règle de proximité ne vaut
    que pour un mot-clé en position d'instruction (début de ligne). Une
    boucle structurellement complète (WHILE ... DO / DONE, REPEAT ... UNTIL)
    reste bloquée où qu'elle soit. Une mention en prose (« aucune boucle
    WHILE/REPEAT n'est nécessaire ») ne bloque plus une réponse valide.
    """

    def _strip_checked_block(match: re.Match) -> str:
        content = match.group(0)
        inner = match.group(1).strip()
        if inner in already_checked_blocks:
            return ""
        return content

    remaining = _FENCED_BLOCK_PATTERN.sub(_strip_checked_block, response)

    lines = remaining.splitlines()
    for i, line in enumerate(lines):
        match = _LOOP_PATTERN.search(line)
        if not match:
            continue
        # 1. Structure de boucle complète (quelle que soit la position) :
        #    `WHILE ... DO` sur la ligne, ou un DONE plus loin ; `REPEAT` suivi
        #    d'un UNTIL plus loin. Ne dépend d'aucune fenêtre : un corps de
        #    boucle long reste détecté.
        after = "\n".join([line[match.end():]] + lines[i + 1:])
        if match.group(1).upper() == "WHILE":
            if _WHILE_DO_PATTERN.search(line) or _DONE_PATTERN.search(after):
                return True
        elif _UNTIL_PATTERN.search(after):
            return True
        # 2. Mot-clé en position d'instruction (début de ligne) avec une
        #    saveur MISPL à proximité : pseudo-code incomplet.
        #    Une simple MENTION du mot-clé au fil d'une phrase (« Aucune boucle
        #    WHILE/REPEAT requise », banc temps réel 2026-09-24, ORD-001) n'est
        #    pas une boucle, même si un accesseur `.Champ` figure à côté.
        if not _STATEMENT_LOOP_PATTERN.match(line):
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
    de refus — que la boucle apparaisse dans un bloc effectivement extrait
    par extract_mispl_blocks (```mispl, ou ``` générique contenant PROGRAM),
    ou ailleurs dans la réponse (fence générique non reconnue par le linter,
    pseudo-code non fenêtré, etc.) ayant une saveur MISPL à proximité. Ne
    fait rien en mode DSI.
    """
    if mode != MODE_TECHNICIEN:
        return response

    # Import différé pour garder src/agent importable sans src/security (et inversement).
    from src.agent.linter import extract_mispl_blocks

    checked_blocks = extract_mispl_blocks(response)
    for block in checked_blocks:
        if _contains_loop(block):
            return REFUSAL_MESSAGE

    if _contains_unfenced_loop(response, checked_blocks):
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
