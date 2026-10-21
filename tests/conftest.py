import os
import pytest
import tempfile
from pathlib import Path
from backend.app.core.config import settings
from backend.app.database.connection import init_db

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Create a fresh temporary SQLite database for each test session/module."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name
    
    monkeypatch.setattr(settings, "DATABASE_PATH", test_db_path)
    init_db()
    
    yield test_db_path
    
    # Teardown
    try:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
    except Exception:
        pass
