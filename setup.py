"""
Script de setup initial du projet MISPL Agent.
Lance : python setup.py
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("MISPL Agent — Setup Initial")
    print("=" * 60)

    # 1. Environnement virtuel
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("\n[1/4] Création de l'environnement virtuel...")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print("     ✅ .venv créé")
    else:
        print("\n[1/4] Environnement virtuel existant ✅")

    # 2. Installation des dépendances
    pip = ".venv/Scripts/pip.exe" if os.name == "nt" else ".venv/bin/pip"
    print("\n[2/4] Installation des dépendances...")
    subprocess.run([pip, "install", "-r", "requirements.txt", "-q"], check=True)
    print("     ✅ Dépendances installées")

    # 3. Vérification des variables d'environnement
    print("\n[3/4] Variables d'environnement...")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        print("     ⚠️  ANTHROPIC_API_KEY non définie")
        print("        Exporter : $env:ANTHROPIC_API_KEY='sk-ant-...'  (PowerShell)")
        print("        Ou créer un fichier .env avec : ANTHROPIC_API_KEY=sk-ant-...")
    else:
        print("     ✅ ANTHROPIC_API_KEY définie")

    # 4. Build du vectorstore
    print("\n[4/4] Construction du vectorstore RAG...")
    python = ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
    confirm = input("     Lancer le build du vectorstore maintenant ? (o/N) : ").strip().lower()
    if confirm == "o":
        subprocess.run([python, "src/rag/build_vectorstore.py"], check=True)
        print("     ✅ Vectorstore construit dans docs/chunks/vectorstore/")
    else:
        print("     Skippé — lancer plus tard : python src/rag/build_vectorstore.py")

    print("\n" + "=" * 60)
    print("✅ Setup terminé !")
    print("\nPour démarrer l'agent :")
    print(f"  {python} src/agent/mispl_agent.py")
    print("\nOu dans Claude Code (ce projet) :")
    print("  Ouvrez ce dossier dans Claude Code et posez vos questions MISPL")
    print("=" * 60)


if __name__ == "__main__":
    main()
