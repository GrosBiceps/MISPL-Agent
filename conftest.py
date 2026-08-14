"""Configuration pytest — ajoute le répertoire racine au sys.path."""

import sys
from pathlib import Path

# Ajoute le répertoire racine du worktree au sys.path
ROOT = Path(__file__).parent.absolute()

def pytest_configure(config):
    """Hook pytest pour configurer sys.path avant la collection de tests."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
