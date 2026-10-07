import pytest
from app.services.crs_service import CRSService
from app.services.measurement_service import MeasurementService

def test_utm_zone_determination():
    epsg_north, name_north = CRSService.get_utm_epsg_for_latlon(12.97, 77.59)
    assert epsg_north == 32643
    assert "32643" in name_north

    epsg_south, name_south = CRSService.get_utm_epsg_for_latlon(-33.86, 151.20)
    assert epsg_south == 32756
    assert "32756" in name_south

def test_polygon_area_measurement():
    poly_geom = {
        "type": "Polygon",
        "coordinates": [[
            [77.5945, 12.9716],
            [77.5995, 12.9716],
            [77.5995, 12.9766],
            [77.5945, 12.9766],
            [77.5945, 12.9716]
        ]]
    }

    geom_type, measurements, proj_crs = MeasurementService.process_feature_measurement(poly_geom, "EPSG:4326")

    assert geom_type == "Polygon"
    assert "32643" in proj_crs
    assert measurements["status"] == "SUCCESS"
    assert measurements["area_sq_m"] > 200000
    assert measurements["area_hectares"] == round(measurements["area_sq_m"] / 10000.0, 6)
    assert measurements["length_m"] is None

def test_linestring_length_measurement():
    line_geom = {
        "type": "LineString",
        "coordinates": [[77.5900, 12.9700], [77.5950, 12.9730], [77.6000, 12.9780]]
    }

    geom_type, measurements, proj_crs = MeasurementService.process_feature_measurement(line_geom, "EPSG:4326")

    assert geom_type == "LineString"
    assert "32643" in proj_crs
    assert measurements["status"] == "SUCCESS"
    assert measurements["length_m"] > 1000
    assert measurements["length_km"] == round(measurements["length_m"] / 1000.0, 6)
    assert measurements["area_sq_m"] is None

def test_point_measurement_handling():
    point_geom = {
        "type": "Point",
        "coordinates": [77.5970, 12.9740]
    }

    geom_type, measurements, proj_crs = MeasurementService.process_feature_measurement(point_geom, "EPSG:4326")

    assert geom_type == "Point"
    assert measurements["status"] == "NOT_APPLICABLE"
    assert measurements["area_sq_m"] is None
    assert measurements["length_m"] is None

def test_unsupported_geometry_graceful_handling():
    unsupported_geom = {
        "type": "UnknownShape",
        "coordinates": []
    }

    geom_type, measurements, proj_crs = MeasurementService.process_feature_measurement(unsupported_geom, "EPSG:4326")

    assert geom_type == "UnknownShape"
    assert measurements["status"] == "UNSUPPORTED"
    assert "not supported" in measurements["note"]
