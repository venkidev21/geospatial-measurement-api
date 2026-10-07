import pytest
from fastapi import status

def test_upload_kml_file(client, sample_kml_bytes):
    response = client.post(
        "/api/files/",
        files={"file": ("survey_site.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "id" in data
    assert data["filename"] == "survey_site.kml"
    assert data["file_type"] == "KML"
    assert data["feature_count"] == 3
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Test GET /api/files/{id}/
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == status.HTTP_200_OK
    assert info_resp.json()["id"] == file_id

    # Test GET /api/files/{id}/measurements/
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == status.HTTP_200_OK
    meas_data = meas_resp.json()
    assert meas_data["file_id"] == file_id
    assert meas_data["feature_count"] == 3
    assert len(meas_data["features"]) == 3

    # Check Summary
    summary = meas_data["summary"]
    assert summary["polygon_count"] == 1
    assert summary["linestring_count"] == 1
    assert summary["point_count"] == 1
    assert summary["total_area_sq_m"] > 0
    assert summary["total_length_m"] > 0

    # Feature 0: Polygon measurements
    feat0 = meas_data["features"][0]
    assert feat0["geometry_type"] == "Polygon"
    assert feat0["crs_projected"] == "EPSG:32643"
    assert feat0["measurements"]["area_sq_m"] > 0
    assert feat0["measurements"]["status"] == "SUCCESS"

    # Feature 2: Point measurements
    feat2 = meas_data["features"][2]
    assert feat2["geometry_type"] == "Point"
    assert feat2["measurements"]["status"] == "NOT_APPLICABLE"

def test_upload_shapefile_zip(client, sample_shapefile_bytes):
    response = client.post(
        "/api/files/",
        files={"file": ("parcel_survey.zip", sample_shapefile_bytes, "application/zip")}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["filename"] == "parcel_survey.zip"
    assert data["file_type"] == "SHAPEFILE"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Check measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == status.HTTP_200_OK
    meas_data = meas_resp.json()
    assert meas_data["summary"]["polygon_count"] == 2

def test_list_files_and_delete(client, sample_kml_bytes):
    # Upload 1 file
    upload_resp = client.post(
        "/api/files/",
        files={"file": ("list_test.kml", sample_kml_bytes, "text/xml")}
    )
    file_id = upload_resp.json()["id"]

    # List files
    list_resp = client.get("/api/files/")
    assert list_resp.status_code == status.HTTP_200_OK
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(f["id"] == file_id for f in list_data["files"])

    # Delete file
    del_resp = client.delete(f"/api/files/{file_id}/")
    assert del_resp.status_code == status.HTTP_200_OK

    # Verify 404 after deletion
    get_del_resp = client.get(f"/api/files/{file_id}/")
    assert get_del_resp.status_code == status.HTTP_404_NOT_FOUND

def test_invalid_file_upload(client):
    response = client.post(
        "/api/files/",
        files={"file": ("invalid_doc.txt", b"Hello world text file", "text/plain")}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported file format" in response.json()["detail"]

def test_nonexistent_file_id(client):
    response = client.get("/api/files/nonexistent_id_999/")
    assert response.status_code == status.HTTP_404_NOT_FOUND
