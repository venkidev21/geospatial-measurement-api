import os
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db_connection

TEST_DB_PATH = "./test_geospatial.db"

@pytest.fixture(scope="function")
def db_conn():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    init_db(TEST_DB_PATH)
    conn = sqlite3.connect(TEST_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

@pytest.fixture(scope="function")
def client(db_conn):
    def override_get_db_connection():
        try:
            yield db_conn
        finally:
            pass

    app.dependency_overrides[get_db_connection] = override_get_db_connection
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_kml_bytes():
    kml_path = os.path.join("sample_data", "sample_survey.kml")
    with open(kml_path, "rb") as f:
        return f.read()

@pytest.fixture
def sample_shapefile_bytes():
    zip_path = os.path.join("sample_data", "sample_shapefile.zip")
    with open(zip_path, "rb") as f:
        return f.read()
