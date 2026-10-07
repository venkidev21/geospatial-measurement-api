import json
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

class GeospatialRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    @staticmethod
    def generate_id() -> str:
        return uuid.uuid4().hex[:12]

    def create_file_record(
        self,
        filename: str,
        file_type: str,
        file_size_bytes: int,
        feature_count: int,
        crs: str
    ) -> Dict[str, Any]:
        file_id = self.generate_id()
        created_at = datetime.now(timezone.utc).isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO geospatial_files 
            (id, filename, file_type, file_size_bytes, feature_count, crs, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (file_id, filename, file_type, file_size_bytes, feature_count, crs, "PROCESSING", created_at)
        )
        self.conn.commit()
        return self.get_file_by_id(file_id)

    def update_file_status(self, file_id: str, status: str, error_message: Optional[str] = None):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE geospatial_files SET status = ?, error_message = ? WHERE id = ?",
            (status, error_message, file_id)
        )
        self.conn.commit()

    def get_file_by_id(self, file_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM geospatial_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def list_files(self, skip: int = 0, limit: int = 50) -> Tuple[int, List[Dict[str, Any]]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM geospatial_files")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT * FROM geospatial_files ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, skip)
        )
        rows = cursor.fetchall()
        return total, [dict(r) for r in rows]

    def delete_file(self, file_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM geospatial_files WHERE id = ?", (file_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def add_features(self, file_id: str, features_data: List[Dict[str, Any]]):
        cursor = self.conn.cursor()
        insert_rows = []

        for feat in features_data:
            insert_rows.append((
                file_id,
                feat["feature_index"],
                feat["geometry_type"],
                json.dumps(feat["geometry"]),
                json.dumps(feat.get("properties", {})),
                feat.get("crs_projected"),
                feat.get("area_sq_m"),
                feat.get("area_hectares"),
                feat.get("area_sq_km"),
                feat.get("length_m"),
                feat.get("length_km"),
                feat.get("measurement_unit", "meters"),
                feat.get("measurement_status", "SUCCESS")
            ))

        cursor.executemany(
            """
            INSERT INTO feature_records (
                file_id, feature_index, geometry_type, geometry, properties,
                crs_projected, area_sq_m, area_hectares, area_sq_km,
                length_m, length_km, measurement_unit, measurement_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows
        )
        self.conn.commit()

    def get_features_by_file_id(self, file_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM feature_records WHERE file_id = ? ORDER BY feature_index ASC",
            (file_id,)
        )
        rows = cursor.fetchall()
        
        result = []
        for r in rows:
            d = dict(r)
            d["geometry"] = json.loads(d["geometry"])
            d["properties"] = json.loads(d["properties"])
            result.append(d)
        return result
