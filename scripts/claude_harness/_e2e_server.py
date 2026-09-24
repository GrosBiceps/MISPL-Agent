"""Lanceur de l'API FastAPI RÉELLE (api.main:app) pour e2e.py, isolée du poste.

Équivalent de `uvicorn api.main:app --host 127.0.0.1 --port <P>` (commande
documentée dans README.md / CLAUDE.md), avec en plus, AVANT l'import de
api.main :
  - garde réseau (toute connexion hors loopback → ExternalNetworkBlocked +
    marqueur bruyant sur stderr, détecté par e2e.py) ;
  - base SQLite de test isolée : api.db.engine / SessionLocal re-pointés vers
    --db (api/db.py code en dur data/mispl.db, jamais touché ici) ;
  - cache et sessions de mispl_agent redirigés vers --workdir.

Les variables MISPL_LLM_BASE_URL (serveur factice loopback) et
OPENROUTER_API_KEY=sk-test-local sont fournies par e2e.py via l'environnement.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()

    base_url = os.environ.get("MISPL_LLM_BASE_URL", "")
    if not base_url.startswith("http://127.0.0.1:"):
        print(f"{C.NETWORK_BLOCK_MARKER} MISPL_LLM_BASE_URL doit pointer sur 127.0.0.1 (reçu {base_url!r})",
              file=sys.stderr)
        return 3
    if os.environ.get("OPENROUTER_API_KEY") != C.FAKE_API_KEY:
        print("OPENROUTER_API_KEY doit valoir la clé factice sk-test-local", file=sys.stderr)
        return 3
    real_db = (C.ROOT / "data" / "mispl.db").resolve()
    if args.db.resolve() == real_db:
        print("Refus : la base de test ne peut pas être data/mispl.db", file=sys.stderr)
        return 3

    C.set_offline_env(llm_base_url=base_url)
    C.install_network_guard()
    sys.path.insert(0, str(C.ROOT))

    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    import api.db as api_db

    engine = create_engine(f"sqlite:///{args.db.resolve().as_posix()}", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", api_db._set_sqlite_pragma)
    api_db.engine = engine
    api_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    api_db.DATABASE_URL = str(engine.url)

    import src.agent.mispl_agent as agent
    args.workdir.mkdir(parents=True, exist_ok=True)
    agent.CACHE_DIR = args.workdir / "cache"
    agent.SESSIONS_DIR = args.workdir / "sessions"
    assert agent.OPENROUTER_BASE_URL == base_url, agent.OPENROUTER_BASE_URL

    import api.main  # noqa: E402  (importé APRÈS le re-pointage de api.db)
    assert api.main.engine is engine

    import uvicorn
    print(f"API e2e : http://127.0.0.1:{args.port} db={args.db} llm={base_url}", flush=True)
    uvicorn.run(api.main.app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
