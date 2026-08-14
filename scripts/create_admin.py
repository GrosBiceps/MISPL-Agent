"""Crée le tout premier compte admin de la plateforme.

Usage : python scripts/create_admin.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from api.admin_bootstrap import create_admin_account  # noqa: E402
from api.db import SessionLocal  # noqa: E402


def main() -> None:
    email = input("Email admin : ").strip()
    display_name = input("Nom affiché : ").strip()
    password = getpass.getpass("Mot de passe (8 caractères min.) : ")
    confirm = getpass.getpass("Confirmer : ")

    if password != confirm:
        print("Les mots de passe ne correspondent pas.")
        sys.exit(1)

    db = SessionLocal()
    try:
        create_admin_account(db, email, display_name, password)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)
    finally:
        db.close()

    print(f"Compte admin créé : {email}")


if __name__ == "__main__":
    main()
