"""
Génère le hash Argon2id du mot de passe DSI (interface Streamlit) et l'écrit
dans .env (MISPL_DSI_PASSWORD_HASH). Supprime l'ancien sel PBKDF2
(MISPL_DSI_PASSWORD_SALT), devenu inutile : le sel Argon2 est inclus dans le hash.

Le hash est écrit entre apostrophes : il contient des « $ », que python-dotenv
laisse intacts entre apostrophes (pas d'interpolation), comme un shell POSIX.

Le mot de passe n'est jamais affiché, journalisé ni écrit : seul son hash
Argon2id (irréversible) est stocké.

Usage : python scripts/set_dsi_password.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from api.security import password_policy_errors  # noqa: E402
from src.security.access_mode import hash_dsi_password  # noqa: E402

ENV_PATH = ROOT / ".env"
HASH_KEY = "MISPL_DSI_PASSWORD_HASH"
LEGACY_SALT_KEY = "MISPL_DSI_PASSWORD_SALT"


def update_env_lines(lines: list[str], password_hash: str) -> list[str]:
    """Remplace (ou ajoute) MISPL_DSI_PASSWORD_HASH et retire l'ancien sel.
    Les autres lignes sont conservées telles quelles."""
    out: list[str] = []
    written = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(f"{LEGACY_SALT_KEY}="):
            continue
        if stripped.startswith(f"{HASH_KEY}="):
            if not written:
                out.append(f"{HASH_KEY}='{password_hash}'\n")
                written = True
            continue
        out.append(line)
    if not written:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(f"{HASH_KEY}='{password_hash}'\n")
    return out


def main() -> None:
    password = getpass.getpass("Nouveau mot de passe DSI : ")
    confirm = getpass.getpass("Confirmer : ")
    if password != confirm:
        print("Les mots de passe ne correspondent pas.")
        sys.exit(1)
    errors = password_policy_errors(password)
    if errors:
        print(" ".join(errors))
        sys.exit(1)

    digest = hash_dsi_password(password)

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True) if ENV_PATH.exists() else []
    ENV_PATH.write_text("".join(update_env_lines(lines, digest)), encoding="utf-8")

    print(f"Mot de passe DSI enregistré (hash Argon2id) dans {ENV_PATH}.")
    print("Redémarrez l'interface Streamlit pour qu'elle relise .env.")


if __name__ == "__main__":
    main()
