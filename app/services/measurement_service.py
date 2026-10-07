import math
import logging
from typing import Dict, Any, Tuple, Optional, List
from app.services.crs_service import CRSService

logger = logging.getLogger(__name__)

class MeasurementService:
    @staticmethod
    def ring_area(ring: List[List[float]]) -> float:
        """Calculates area of a 2D closed polygon ring using Shoelace formula in square meters."""
        n = len(ring)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += ring[i][0] * ring[j][1]
            area -= ring[j][0] * ring[i][1]
        return abs(area) / 2.0

    @classmethod
    def polygon_area(cls, polygon_coords: List[Any]) -> float:
        """Calculates net area for a Polygon (outer shell minus inner holes)."""
        if not polygon_coords or len(polygon_coords) == 0:
            return 0.0
        outer_area = cls.ring_area(polygon_coords[0])
        holes_area = sum(cls.ring_area(hole) for hole in polygon_coords[1:])
        return max(0.0, outer_area - holes_area)

    @classmethod
    def linestring_length(cls, line_coords: List[List[float]]) -> float:
        """Calculates total Euclidean length for a 2D line segment array in meters."""
        if not line_coords or len(line_coords) < 2:
            return 0.0
        length = 0.0
        for i in range(len(line_coords) - 1):
            dx = line_coords[i+1][0] - line_coords[i][0]
            dy = line_coords[i+1][1] - line_coords[i][1]
            length += math.sqrt(dx * dx + dy * dy)
        return length

    @classmethod
    def process_feature_measurement(
        cls,
        geometry_dict: Dict[str, Any],
        src_crs_str: str = "EPSG:4326"
    ) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """
        Processes a GeoJSON geometry dict, projects it into metric UTM coordinates,
        and calculates feature measurements (Area for Polygons, Length for LineStrings, None for Points).
        
        Returns:
            (geometry_type, measurement_dict, projected_crs_name)
        """
        if not geometry_dict or "type" not in geometry_dict or "coordinates" not in geometry_dict:
            return (
                "Unknown",
                {
                    "area_sq_m": None,
                    "area_hectares": None,
                    "area_sq_km": None,
                    "length_m": None,
                    "length_km": None,
                    "unit": "meters",
                    "status": "UNSUPPORTED",
                    "note": "Geometry is empty or missing coordinates"
                },
                None
            )

        geom_type = geometry_dict["type"]

        # Project geometry to UTM metric coordinates
        try:
            projected_geom, proj_crs_str = CRSService.project_geojson_geometry(geometry_dict)
            coords = projected_geom.get("coordinates", [])
        except Exception as e:
            logger.error(f"Error projecting geometry ({geom_type}): {e}")
            return (
                geom_type,
                {
                    "area_sq_m": None,
                    "area_hectares": None,
                    "area_sq_km": None,
                    "length_m": None,
                    "length_km": None,
                    "unit": "meters",
                    "status": "UNSUPPORTED",
                    "note": f"Reprojection error: {str(e)}"
                },
                None
            )

        # Polygon / MultiPolygon -> Area calculation
        if geom_type == "Polygon":
            try:
                area_sq_m = round(cls.polygon_area(coords), 4)
                return (
                    geom_type,
                    {
                        "area_sq_m": area_sq_m,
                        "area_hectares": round(area_sq_m / 10000.0, 6),
                        "area_sq_km": round(area_sq_m / 1000000.0, 6),
                        "length_m": None,
                        "length_km": None,
                        "unit": "meters",
                        "status": "SUCCESS"
                    },
                    proj_crs_str
                )
            except Exception as e:
                logger.error(f"Error calculating polygon area: {e}")
                return (
                    geom_type,
                    {
                        "area_sq_m": None,
                        "area_hectares": None,
                        "area_sq_km": None,
                        "length_m": None,
                        "length_km": None,
                        "unit": "meters",
                        "status": "UNSUPPORTED",
                        "note": f"Calculation error: {str(e)}"
                    },
                    proj_crs_str
                )

        elif geom_type == "MultiPolygon":
            try:
                total_area = sum(cls.polygon_area(p) for p in coords)
                area_sq_m = round(total_area, 4)
                return (
                    geom_type,
                    {
                        "area_sq_m": area_sq_m,
                        "area_hectares": round(area_sq_m / 10000.0, 6),
                        "area_sq_km": round(area_sq_m / 1000000.0, 6),
                        "length_m": None,
                        "length_km": None,
                        "unit": "meters",
                        "status": "SUCCESS"
                    },
                    proj_crs_str
                )
            except Exception as e:
                return (
                    geom_type,
                    {
                        "area_sq_m": None,
                        "area_hectares": None,
                        "area_sq_km": None,
                        "length_m": None,
                        "length_km": None,
                        "unit": "meters",
                        "status": "UNSUPPORTED",
                        "note": f"Calculation error: {str(e)}"
                    },
                    proj_crs_str
                )

        # LineString / MultiLineString -> Length calculation
        elif geom_type == "LineString":
            try:
                length_m = round(cls.linestring_length(coords), 4)
                return (
                    geom_type,
                    {
                        "area_sq_m": None,
                        "area_hectares": None,
                        "area_sq_km": None,
                        "length_m": length_m,
                        "length_km": round(length_m / 1000.0, 6),
                        "unit": "meters",
                        "status": "SUCCESS"
                    },
                    proj_crs_str
                )
            except Exception as e:
                return (
                    geom_type,
                    {
                        "area_sq_m": None,
                        "area_hectares": None,
                        "area_sq_km": None,
                        "length_m": None,
                        "length_km": None,
                        "unit": "meters",
                        "status": "UNSUPPORTED",
                        "note": f"Calculation error: {str(e)}"
                    },
                    proj_crs_str
                )

        elif geom_type == "MultiLineString":
            try:
                total_len = sum(cls.linestring_length(l) for l in coords)
                length_m = round(total_len, 4)
                return (
                    geom_type,
                    {
                        "area_sq_m": None,
                        "area_hectares": None,
                        "area_sq_km": None,
                        "length_m": length_m,
                        "length_km": round(length_m / 1000.0, 6),
                        "unit": "meters",
                        "status": "SUCCESS"
                    },
                    proj_crs_str
                )
            except Exception as e:
                return (
                    geom_type,
                    {
                        "area_sq_m": None,
                        "area_hectares": None,
                        "area_sq_km": None,
                        "length_m": None,
                        "length_km": None,
                        "unit": "meters",
                        "status": "UNSUPPORTED",
                        "note": f"Calculation error: {str(e)}"
                    },
                    proj_crs_str
                )

        # Point / MultiPoint -> No measurement required
        elif geom_type in ["Point", "MultiPoint"]:
            return (
                geom_type,
                {
                    "area_sq_m": None,
                    "area_hectares": None,
                    "area_sq_km": None,
                    "length_m": None,
                    "length_km": None,
                    "unit": "meters",
                    "status": "NOT_APPLICABLE",
                    "note": "Point geometry - measurement not applicable"
                },
                proj_crs_str
            )

        # Graceful handling for unsupported geometry types
        else:
            return (
                geom_type,
                {
                    "area_sq_m": None,
                    "area_hectares": None,
                    "area_sq_km": None,
                    "length_m": None,
                    "length_km": None,
                    "unit": "meters",
                    "status": "UNSUPPORTED",
                    "note": f"Geometry type '{geom_type}' measurement not supported"
                },
                proj_crs_str
            )
