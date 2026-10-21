import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.logging import logger

def get_db_path() -> str:
    db_path = settings.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    return db_path

def init_db():
    """Initialize database tables from schema.sql."""
    db_path = get_db_path()
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(schema_sql)
        conn.commit()
    logger.info(f"Initialized SQLite database at {db_path}")

    # Reconcile any orphaned runs from previous abnormal terminations
    try:
        from backend.app.database.repository import DatabaseRepository
        reconciled = DatabaseRepository.reconcile_orphaned_runs()
        if reconciled > 0:
            logger.info(f"Reconciled {reconciled} previously orphaned runs to terminal FAILED status.")
    except Exception as e:
        logger.warning(f"Orphaned run reconciliation skipped: {e}")

@contextmanager
def get_db_connection():
    """Context manager for SQLite connections with foreign keys enabled."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()
