import pathlib
import tempfile

import config
from core import database


def fresh_env():
    """Point the app at a brand-new temp database and model folder."""
    from ml import categorizer
    d = pathlib.Path(tempfile.mkdtemp())
    config.DB_PATH = d / "test.db"
    config.MODEL_DIR = d / "models"
    categorizer._CACHE.clear()
    database.init_db()
    return d
