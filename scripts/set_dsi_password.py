"""
Génère le hash + sel du mot de passe DSI et les écrit/met à jour dans .env.

Usage : python scripts/set_dsi_password.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.security.access_mode import generate_salt, hash_password  # noqa: E402

ENV_PATH = ROOT / ".env"


def _upsert_env_var(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"{key}="
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = f"{prefix}{value}\n"
            return lines
    lines.append(f"{prefix}{value}\n")
    return lines


def main() -> None:
    password = getpass.getpass("Nouveau mot de passe DSI : ")
    confirm = getpass.getpass("Confirmer : ")
    if password != confirm:
        print("Les mots de passe ne correspondent pas.")
        sys.exit(1)
    if len(password) < 8:
        print("Le mot de passe doit faire au moins 8 caractères.")
        sys.exit(1)

    salt = generate_salt()
    digest = hash_password(password, salt)

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True) if ENV_PATH.exists() else []
    lines = _upsert_env_var(lines, "MISPL_DSI_PASSWORD_SALT", salt)
    lines = _upsert_env_var(lines, "MISPL_DSI_PASSWORD_HASH", digest)
    ENV_PATH.write_text("".join(lines), encoding="utf-8")

    print(f"Mot de passe DSI enregistré dans {ENV_PATH}.")


if __name__ == "__main__":
    main()
