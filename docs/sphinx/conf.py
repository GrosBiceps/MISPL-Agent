"""Configuration Sphinx — documentation d'ingénierie MISPL Agent.

Construit la documentation à partir des fichiers Markdown (MyST) de
docs/specifications/, docs/architecture/ (y compris adr/), docs/guides/,
docs/base_de_donnees/, docs/cartographie/ et docs/securite/.

Build :
    sphinx-build -b html docs/sphinx docs/sphinx/_build/html
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# -- Rendre visibles les sources situées hors de docs/sphinx/ -----------------
#
# Sphinx ne découvre que les documents situés SOUS son répertoire source
# (docs/sphinx/, imposé par la commande de build documentée :
# `sphinx-build -b html docs/sphinx docs/sphinx/_build/html`). Les
# spécifications, l'architecture, les guides et les dossiers rédigés par
# d'autres agents (base de données, cartographie, sécurité) vivent à dessein
# sous docs/ (pas sous docs/sphinx/), pour rester lisibles directement sur
# GitHub sans dépendre de Sphinx. On les recopie donc ici avant la
# construction, dans des dossiers ignorés par Git (voir .gitignore :
# docs/sphinx/_build/ ; les dossiers copiés ci-dessous portent un préfixe
# "_src_" pour ne jamais être confondus avec des sources versionnées).
_DOCS_ROOT = Path(__file__).resolve().parent.parent
_SPHINX_ROOT = Path(__file__).resolve().parent
_MIRRORED_DIRS = [
    "specifications",
    "architecture",
    "guides",
    "base_de_donnees",
    "cartographie",
    "securite",
]

for _name in _MIRRORED_DIRS:
    _source = _DOCS_ROOT / _name
    _dest = _SPHINX_ROOT / f"_src_{_name}"
    if _dest.exists():
        shutil.rmtree(_dest)
    if _source.is_dir():
        shutil.copytree(
            _source,
            _dest,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

# -- Informations sur le projet ----------------------------------------------

project = "MISPL Agent"
author = "Équipe MISPL Agent"
copyright = "2026, Équipe MISPL Agent"

# -- Extensions ----------------------------------------------------------------

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
]

# MyST : autoriser les fences ```{directive} ``` et les liens Markdown standards
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
]

# Convertit automatiquement les blocs de code ```mermaid (syntaxe Markdown
# standard, lisible directement sur GitHub) en directive {mermaid} de
# sphinxcontrib-mermaid, pour qu'ils soient rendus comme des diagrammes dans
# le HTML Sphinx plutôt que comme du texte préformaté brut.
myst_fence_as_directive = ["mermaid"]

# Sources Markdown uniquement pour cette documentation
source_suffix = {
    ".md": "markdown",
}

# -- Langue ----------------------------------------------------------------

language = "fr"

# -- Fichiers à ignorer ----------------------------------------------------

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

# -- Thème HTML ----------------------------------------------------------------

try:
    import furo  # noqa: F401

    html_theme = "furo"
except ImportError:
    html_theme = "sphinx_rtd_theme"

html_title = "MISPL Agent — Documentation d'ingénierie"

# -- Mermaid -----------------------------------------------------------------

# sphinxcontrib-mermaid rend les blocs ```mermaid directement (pris en charge
# nativement par myst-parser pour les fences de code marquées "mermaid").
mermaid_version = "latest"
