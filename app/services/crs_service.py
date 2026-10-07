import math
import logging
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

class CRSService:
    WGS84_A = 6378137.0  # Semi-major axis in meters
    WGS84_F = 1.0 / 298.257223563  # Flattening

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> str:
        """
        Parses and standardizes CRS input string.
        Defaults to 'EPSG:4326' (WGS84 geographic) if empty or unparseable.
        """
        if not crs_input:
            return "EPSG:4326"
        
        crs_clean = crs_input.strip().upper()
        if "4326" in crs_clean or "WGS84" in crs_clean or "GEOGCS" in crs_clean:
            return "EPSG:4326"
        elif crs_clean.startswith("EPSG:"):
            return crs_clean
        elif crs_clean.isdigit():
            return f"EPSG:{crs_clean}"
        else:
            return "EPSG:4326"

    @staticmethod
    def get_utm_epsg_for_latlon(lat: float, lon: float) -> Tuple[int, str]:
        """
        Determines the UTM zone EPSG code and formatted name for a given (lat, lon).
        WGS 84 / UTM North: EPSG 32601 to 32660
        WGS 84 / UTM South: EPSG 32701 to 32760
        """
        lon_clamped = max(-180.0, min(180.0, lon))
        lat_clamped = max(-90.0, min(90.0, lat))

        zone = int((lon_clamped + 180) / 6) + 1
        zone = max(1, min(60, zone))

        if lat_clamped >= 0:
            epsg = 32600 + zone
            name = f"EPSG:{epsg} (WGS 84 / UTM Zone {zone}N)"
        else:
            epsg = 32700 + zone
            name = f"EPSG:{epsg} (WGS 84 / UTM Zone {zone}S)"

        return epsg, f"EPSG:{epsg}"

    @classmethod
    def latlon_to_utm(cls, lat: float, lon: float) -> Tuple[float, float, int]:
        """
        Converts (lat, lon) in WGS84 degrees to UTM (Easting, Northing) in meters.
        Returns: (easting, northing, epsg_code)
        """
        a = cls.WGS84_A
        f = cls.WGS84_F
        b = a * (1 - f)
        e2 = (a**2 - b**2) / a**2
        ep2 = (a**2 - b**2) / b**2
        k0 = 0.9996

        lon_clamped = max(-180.0, min(180.0, lon))
        lat_clamped = max(-80.0, min(84.0, lat))  # Standard UTM valid latitude bounds

        zone = int((lon_clamped + 180) / 6) + 1
        zone = max(1, min(60, zone))
        lon0 = (zone - 1) * 6 - 180 + 3

        phi = math.radians(lat_clamped)
        lam = math.radians(lon_clamped)
        lam0 = math.radians(lon0)
        dlam = lam - lam0

        N = a / math.sqrt(1 - e2 * math.sin(phi)**2)
        T = math.tan(phi)**2
        C = ep2 * math.cos(phi)**2
        A = math.cos(phi) * dlam

        M = a * (
            (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * phi
            - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*phi)
            + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*phi)
            - (35*e2**3/3072) * math.sin(6*phi)
        )

        easting = 500000.0 + k0 * N * (
            A + (1 - T + C) * A**3 / 6.0
            + (5 - 18*T + T**2 + 72*C - 58*ep2) * A**5 / 120.0
        )

        northing = k0 * (
            M + N * math.tan(phi) * (
                A**2 / 2.0
                + (5 - T + 9*C + 4*C**2) * A**4 / 24.0
                + (61 - 58*T + T**2 + 600*C - 330*ep2) * A**6 / 720.0
            )
        )

        if lat < 0:
            northing += 10000000.0

        epsg = 32600 + zone if lat >= 0 else 32700 + zone
        return easting, northing, epsg

    @classmethod
    def compute_centroid_latlon(cls, coordinates: Any) -> Tuple[float, float]:
        """
        Computes the average (centroid) lat/lon for any nested coordinate structure.
        """
        all_lats = []
        all_lons = []

        def extract_coords(c):
            if not c:
                return
            if isinstance(c[0], (int, float)):
                if len(c) >= 2:
                    all_lons.append(float(c[0]))
                    all_lats.append(float(c[1]))
            else:
                for sub in c:
                    extract_coords(sub)

        extract_coords(coordinates)

        if not all_lats or not all_lons:
            return 0.0, 0.0

        avg_lat = sum(all_lats) / len(all_lats)
        avg_lon = sum(all_lons) / len(all_lons)
        return avg_lat, avg_lon

    @classmethod
    def project_geojson_geometry(cls, geometry_dict: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Projects a GeoJSON geometry dict (Polygon, LineString, Point, etc.)
        from geographic coordinates (lat, lon) into projected UTM metric coordinates (x, y).
        
        Returns: (projected_geometry_dict, projected_epsg_code_string)
        """
        if not geometry_dict or "coordinates" not in geometry_dict:
            return geometry_dict, "EPSG:32631"

        coords = geometry_dict["coordinates"]
        avg_lat, avg_lon = cls.compute_centroid_latlon(coords)
        epsg_code, epsg_str = cls.get_utm_epsg_for_latlon(avg_lat, avg_lon)

        def project_coords(c):
            if not c:
                return c
            if isinstance(c[0], (int, float)):
                lon, lat = float(c[0]), float(c[1])
                easting, northing, _ = cls.latlon_to_utm(lat, lon)
                return [round(easting, 4), round(northing, 4)]
            else:
                return [project_coords(sub) for sub in c]

        projected_coords = project_coords(coords)
        projected_geom = {
            "type": geometry_dict.get("type"),
            "coordinates": projected_coords
        }

        return projected_geom, epsg_str
