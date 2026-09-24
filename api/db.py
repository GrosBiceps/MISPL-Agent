"""Connexion SQLite + base déclarative SQLAlchemy pour l'API MISPL Agent."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'mispl.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Active l'enforcement des clés étrangères SQLite (désactivé par défaut) et
    un délai d'attente sur verrou plutôt qu'un échec immédiat sous charge
    concurrente (plusieurs utilisateurs écrivant en même temps)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Colonnes ajoutées après la création initiale du schéma. create_all() ne
# modifie jamais une table existante : sans cette étape, une base créée avant
# l'ajout d'une colonne ferait échouer toute requête ORM sur la table.
# Chaque entrée : (table, colonne, définition SQL avec valeur par défaut).
_ADDED_COLUMNS = (
    ("users", "must_change_password", "BOOLEAN NOT NULL DEFAULT 0"),
)


def upgrade_schema(bind=None) -> list[str]:
    """Crée les tables manquantes puis ajoute les colonnes manquantes
    (ALTER TABLE ... ADD COLUMN, non destructif, idempotent). Ne supprime ni
    ne modifie jamais une donnée existante. Retourne la liste des colonnes
    ajoutées (pour journalisation / tests)."""
    import api.models  # noqa: F401 — enregistre toutes les tables dans Base.metadata

    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    added: list[str] = []
    with bind.begin() as conn:
        inspector = inspect(conn)
        for table, column, ddl in _ADDED_COLUMNS:
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                added.append(f"{table}.{column}")
    return added
