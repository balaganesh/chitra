"""
Storage initialization script.

Creates data directories and initializes SQLite databases for all capabilities.
Safe to run multiple times — uses CREATE TABLE IF NOT EXISTS.
"""

import logging
import os
import sqlite3

from storage.schema import SCHEMAS

logger = logging.getLogger(__name__)


def setup_storage():
    """Create data directories and initialize all capability databases."""
    data_dir = os.environ.get("CHITRA_DATA_DIR", os.path.expanduser("~/.chitra/data"))

    # Create directory structure
    for subdir in ["", "tts", "logs"]:
        path = os.path.join(data_dir, subdir) if subdir else data_dir
        os.makedirs(path, exist_ok=True)
        logger.info("Directory: %s", path)

    # Initialize each capability database
    for capability_name, (db_filename, schema_sql) in SCHEMAS.items():
        db_path = os.path.join(data_dir, db_filename)
        conn = sqlite3.connect(db_path)
        conn.execute(schema_sql)
        conn.commit()
        conn.close()
        logger.info("Initialized: %s → %s", capability_name, db_path)

    logger.info("Storage setup complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_storage()
