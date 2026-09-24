"""Hachage de mot de passe (Argon2id), politique de mot de passe et génération
de mot de passe temporaire pour les comptes de l'API.

Le hachage lui-même (paramètres Argon2id figés, vérification, détection du
besoin de re-hachage) vit dans src/security/password_hashing.py, partagé avec
le mot de passe DSI de l'interface Streamlit. Justification des paramètres :
docs/securite/NOTE_RSSI_HACHAGE_MOTS_DE_PASSE.md.
"""

from __future__ import annotations

import secrets
import string

from src.security.password_hashing import (  # noqa: F401 — ré-export public
    ARGON2_HASH_LEN,
    ARGON2_MEMORY_COST_KIB,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LEN,
    ARGON2_TIME_COST,
    hash_password,
    needs_rehash,
    verify_password,
)

# Alphabet des mots de passe temporaires : 70 symboles, 14 caractères
# -> log2(70) * 14 ≈ 85,8 bits d'entropie (tirage secrets.choice, CSPRNG).
_TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"

# ── Politique de mot de passe choisi par l'utilisateur ─────────────────────────
PASSWORD_MIN_LENGTH = 12
PASSPHRASE_MIN_LENGTH = 16
PASSWORD_MAX_LENGTH = 256  # cohérent avec LoginRequest (api/schemas.py)

# Liste courte de mots de passe notoirement compromis ou triviaux (comparaison
# insensible à la casse, sur le mot de passe entier). Complément, pas substitut,
# d'un contrôle contre une vraie liste de fuites (à arbitrer : cf. note RSSI).
_COMMON_PASSWORDS = frozenset({
    "123456789012", "1234567890ab", "azertyuiop12", "azertyuiopqs", "qwertyuiop12",
    "motdepasse123", "motdepasse1234", "motdepasse!123", "password1234", "password123!",
    "passw0rd1234", "administrateur", "admin1234567", "bonjour12345", "soleil123456",
    "laboratoire1", "laboratoire123", "glims1234567", "mispl1234567", "chu123456789",
    "000000000000", "111111111111", "aaaaaaaaaaaa", "azerty123456", "qwerty123456",
})


def generate_temp_password(length: int = 14) -> str:
    return "".join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length))


def _character_classes(password: str) -> int:
    return sum((
        any(c.islower() for c in password),
        any(c.isupper() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ))


def password_policy_errors(password: str, *, email: str | None = None, display_name: str | None = None) -> list[str]:
    """Liste des manquements à la politique (vide = conforme).

    Règles : 12 caractères minimum avec au moins 3 des 4 familles (minuscules,
    majuscules, chiffres, autres), OU phrase de passe d'au moins 16 caractères ;
    256 caractères maximum ; ne doit pas contenir l'identifiant (partie locale
    de l'email) ni le nom affiché ; ne doit pas figurer dans la liste des mots
    de passe triviaux. Les messages ne reprennent jamais le mot de passe.
    """
    errors: list[str] = []
    if len(password) > PASSWORD_MAX_LENGTH:
        errors.append(f"Le mot de passe ne doit pas dépasser {PASSWORD_MAX_LENGTH} caractères.")
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Le mot de passe doit faire au moins {PASSWORD_MIN_LENGTH} caractères.")
    elif len(password) < PASSPHRASE_MIN_LENGTH and _character_classes(password) < 3:
        errors.append(
            "Le mot de passe doit combiner au moins 3 familles de caractères "
            "(minuscules, majuscules, chiffres, caractères spéciaux), "
            f"ou être une phrase de passe d'au moins {PASSPHRASE_MIN_LENGTH} caractères."
        )
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS or len(set(password)) <= 2:
        errors.append("Ce mot de passe est trop courant ou trop prévisible.")
    identifiers = []
    if email:
        identifiers.append(email.split("@", 1)[0].lower())
    if display_name:
        identifiers.extend(part.lower() for part in display_name.split())
    if any(len(ident) >= 4 and ident in lowered for ident in identifiers):
        errors.append("Le mot de passe ne doit pas contenir votre identifiant ni votre nom.")
    return errors
