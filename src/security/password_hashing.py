"""Hachage Argon2id partagé — source unique des paramètres pour l'API
(comptes, api/security.py) et pour le mot de passe DSI de Streamlit
(src/security/access_mode.py).

Paramètres figés explicitement (et non hérités des valeurs par défaut
d'argon2-cffi) : une montée de version de la bibliothèque ne doit jamais
changer silencieusement le coût de hachage. Ils correspondent au second
profil recommandé par la RFC 9106 (§4 : t = 3, p = 4, m = 64 Mio, sel de
128 bits, empreinte de 256 bits) et dépassent le minimum OWASP (m = 19 Mio,
t = 2, p = 1). Justification : docs/securite/NOTE_RSSI_HACHAGE_MOTS_DE_PASSE.md.

Un hachage n'est jamais « déchiffrable » : aucune fonction de ce module ne
permet de retrouver un mot de passe. La seule opération possible est de
vérifier qu'un mot de passe candidat correspond à un hachage.
"""

from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

ARGON2_TIME_COST = 3            # itérations
ARGON2_MEMORY_COST_KIB = 65536  # 64 Mio
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32            # 256 bits
ARGON2_SALT_LEN = 16            # 128 bits, tiré par os.urandom dans argon2-cffi

_hasher = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST_KIB,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LEN,
    salt_len=ARGON2_SALT_LEN,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Retourne le hachage Argon2id (format PHC, sel aléatoire inclus)."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Vérifie un mot de passe candidat. Ne lève jamais : un hachage illisible
    ou une incohérence de paramètres vaut « non ». La comparaison finale est à
    temps constant (implémentation de référence Argon2, argon2_verify)."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True si le hachage a été produit avec d'autres paramètres (ou une autre
    variante) que la configuration courante : il doit être recalculé au
    prochain moment où le mot de passe en clair est connu (connexion réussie)."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, ValueError):
        return True


def is_argon2_hash(value: str) -> bool:
    return value.startswith("$argon2")
