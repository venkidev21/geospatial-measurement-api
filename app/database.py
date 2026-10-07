import sqlite3
import logging
from typing import Generator
from app.config import settings

logger = logging.getLogger(__name__)

def get_db_path() -> str:
    if settings.DATABASE_URL.startswith("sqlite:///"):
        return settings.DATABASE_URL.replace("sqlite:///", "")
    return "./geospatial_api.db"

def init_db(db_path: str = None):
    """Initializes SQLite database tables and foreign key constraints."""
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geospatial_files (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL DEFAULT 0,
        feature_count INTEGER NOT NULL DEFAULT 0,
        crs TEXT NOT NULL DEFAULT 'EPSG:4326',
        status TEXT NOT NULL DEFAULT 'PROCESSING',
        error_message TEXT,
        created_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feature_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT NOT NULL,
        feature_index INTEGER NOT NULL,
        geometry_type TEXT NOT NULL,
        geometry TEXT NOT NULL,
        properties TEXT NOT NULL,
        crs_projected TEXT,
        area_sq_m REAL,
        area_hectares REAL,
        area_sq_km REAL,
        length_m REAL,
        length_km REAL,
        measurement_unit TEXT NOT NULL DEFAULT 'meters',
        measurement_status TEXT NOT NULL DEFAULT 'SUCCESS',
        FOREIGN KEY (file_id) REFERENCES geospatial_files(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    logger.info(f"Initialized SQLite database at {db_path}")

def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Dependency provider for SQLite database connection."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()
