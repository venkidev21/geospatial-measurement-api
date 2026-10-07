import os
import zipfile
import tempfile
import logging
from typing import List, Dict, Any, Tuple
import shapefile

logger = logging.getLogger(__name__)

class ShapefileParser:
    @staticmethod
    def parse_zip(zip_path_or_bytes: Any) -> Tuple[List[Dict[str, Any]], str]:
        """
        Parses a .zip archive containing a Shapefile (.shp, .shx, .dbf, and optional .prj).
        
        Returns:
            (features_list, crs_string)
            where features_list contains dicts with keys:
            'feature_index', 'geometry_geojson', 'properties'
        """
        temp_dir = tempfile.mkdtemp(prefix="shp_parse_")
        try:
            if isinstance(zip_path_or_bytes, bytes):
                zip_temp_path = os.path.join(temp_dir, "uploaded.zip")
                with open(zip_temp_path, "wb") as f:
                    f.write(zip_path_or_bytes)
                archive_path = zip_temp_path
            else:
                archive_path = zip_path_or_bytes

            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            shp_path = None
            prj_path = None
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.lower().endswith(".shp"):
                        shp_path = os.path.join(root, file)
                    elif file.lower().endswith(".prj"):
                        prj_path = os.path.join(root, file)

            if not shp_path:
                raise ValueError("Invalid Shapefile archive: No .shp file found in .zip archive.")

            crs_str = "EPSG:4326"
            if prj_path and os.path.exists(prj_path):
                try:
                    with open(prj_path, 'r', encoding='utf-8', errors='ignore') as prj_file:
                        prj_content = prj_file.read().strip()
                        if prj_content:
                            if "326" in prj_content or "UTM" in prj_content:
                                crs_str = prj_content
                            else:
                                crs_str = "EPSG:4326"
                except Exception as e:
                    logger.warning(f"Failed to read .prj file {prj_path}: {e}")

            features = []
            with shapefile.Reader(shp_path) as reader:
                fields = [f[0] for f in reader.fields[1:]]
                
                for idx, shape_rec in enumerate(reader.iterShapeRecords()):
                    try:
                        geo_interface = shape_rec.shape.__geo_interface__
                        if not geo_interface or not geo_interface.get("coordinates"):
                            logger.warning(f"Feature at index {idx} has empty shape geometry.")
                            continue

                        # Clean property values for JSON compatibility
                        record_dict = {}
                        raw_record = shape_rec.record.as_dict() if hasattr(shape_rec.record, 'as_dict') else dict(zip(fields, shape_rec.record))
                        
                        for k, v in raw_record.items():
                            if isinstance(v, (bytes, bytearray)):
                                record_dict[str(k)] = v.decode('utf-8', errors='replace')
                            elif hasattr(v, 'isoformat'):
                                record_dict[str(k)] = v.isoformat()
                            else:
                                record_dict[str(k)] = v

                        features.append({
                            "feature_index": idx,
                            "geometry_geojson": geo_interface,
                            "properties": record_dict
                        })
                    except Exception as feat_err:
                        logger.error(f"Error reading shape feature index {idx}: {feat_err}")
                        continue

            return features, crs_str

        finally:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
