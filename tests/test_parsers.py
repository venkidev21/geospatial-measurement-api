import pytest
from app.services.kml_parser import KMLParser
from app.services.shapefile_parser import ShapefileParser

def test_kml_parser(sample_kml_bytes):
    features, crs_str = KMLParser.parse_kml(sample_kml_bytes)
    
    assert crs_str == "EPSG:4326"
    assert len(features) == 3

    # Feature 0: Polygon
    feat0 = features[0]
    assert feat0["feature_index"] == 0
    assert feat0["geometry_geojson"]["type"] == "Polygon"
    assert feat0["properties"].get("name") == "Central City Park"
    assert feat0["properties"].get("zone_type") == "Park"

    # Feature 1: LineString
    feat1 = features[1]
    assert feat1["feature_index"] == 1
    assert feat1["geometry_geojson"]["type"] == "LineString"
    assert feat1["properties"].get("name") == "Grand Expressway"

    # Feature 2: Point
    feat2 = features[2]
    assert feat2["feature_index"] == 2
    assert feat2["geometry_geojson"]["type"] == "Point"
    assert feat2["properties"].get("name") == "Weather Station #1"

def test_shapefile_parser(sample_shapefile_bytes):
    features, crs_str = ShapefileParser.parse_zip(sample_shapefile_bytes)
    
    assert "4326" in crs_str or "EPSG" in crs_str
    assert len(features) == 2

    feat0 = features[0]
    assert feat0["geometry_geojson"]["type"] == "Polygon"
    assert feat0["properties"].get("NAME") == "Agri Field A"
    assert feat0["properties"].get("CATEGORY") == "Agriculture"

    feat1 = features[1]
    assert feat1["geometry_geojson"]["type"] == "Polygon"
    assert feat1["properties"].get("NAME") == "Industrial Tech Park"
