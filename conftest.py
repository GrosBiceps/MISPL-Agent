"""Configuration pytest — ajoute le répertoire racine au sys.path."""

import os
import sys
from pathlib import Path

# Neutralise le mode routeur LLM du .env local (MISPL_LLM_*) : load_dotenv
# (api/main.py, app.py) ne surcharge pas une variable déjà définie, donc les
# tests ne partent jamais vers le routeur réel. Les tests du mode routeur
# (tests/agent/test_llm_router_mode.py) le réactivent via monkeypatch.
os.environ["MISPL_LLM_MODEL"] = ""
os.environ["MISPL_LLM_BASE_URL"] = "https://openrouter.ai/api/v1"

# Ajoute le répertoire racine du worktree au sys.path
ROOT = Path(__file__).parent.absolute()

def pytest_configure(config):
    """Hook pytest pour configurer sys.path avant la collection de tests."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
