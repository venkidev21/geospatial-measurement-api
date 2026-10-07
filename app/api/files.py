import os
import sqlite3
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from app.database import get_db_connection
from app.repositories.geospatial_repository import GeospatialRepository
from app.schemas.geospatial import (
    FileInfoResponse,
    FileMeasurementsResponse,
    FeatureResponse,
    MeasurementDetail,
    MeasurementSummary,
    FileListResponse
)
from app.services.shapefile_parser import ShapefileParser
from app.services.kml_parser import KMLParser
from app.services.crs_service import CRSService
from app.services.measurement_service import MeasurementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Geospatial Files"])

@router.post("/", response_model=FileInfoResponse, status_code=status.HTTP_201_CREATED)
async def upload_geospatial_file(
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db_connection)
):
    """
    Uploads and processes a geospatial file (.zip containing Shapefile or .kml).
    Extracts features, calculates measurements using an appropriate projected CRS (UTM),
    and stores the processed file data.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided or filename is empty."
        )

    filename = file.filename
    filename_lower = filename.lower()
    
    file_type = None
    if filename_lower.endswith(".zip"):
        file_type = "SHAPEFILE"
    elif filename_lower.endswith(".kml") or filename_lower.endswith(".xml"):
        file_type = "KML"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a .zip archive (Shapefile) or a .kml file."
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        # Parse features based on file type
        if file_type == "SHAPEFILE":
            features_raw, crs_str = ShapefileParser.parse_zip(content)
        else:
            features_raw, crs_str = KMLParser.parse_kml(content)

        src_crs = CRSService.parse_crs(crs_str)
        repo = GeospatialRepository(conn)

        # Create GeospatialFile database record
        file_record = repo.create_file_record(
            filename=filename,
            file_type=file_type,
            file_size_bytes=len(content),
            feature_count=len(features_raw),
            crs=src_crs
        )

        file_id = file_record["id"]

        # Process each feature and calculate measurements
        features_to_save = []
        for feat in features_raw:
            feat_idx = feat["feature_index"]
            geojson_geom = feat["geometry_geojson"]
            props = feat["properties"]

            geom_type, measurement_dict, proj_crs = MeasurementService.process_feature_measurement(
                geometry_dict=geojson_geom,
                src_crs_str=src_crs
            )

            features_to_save.append({
                "feature_index": feat_idx,
                "geometry_type": geom_type,
                "geometry": geojson_geom,
                "properties": props,
                "crs_projected": proj_crs,
                "area_sq_m": measurement_dict.get("area_sq_m"),
                "area_hectares": measurement_dict.get("area_hectares"),
                "area_sq_km": measurement_dict.get("area_sq_km"),
                "length_m": measurement_dict.get("length_m"),
                "length_km": measurement_dict.get("length_km"),
                "measurement_unit": measurement_dict.get("unit", "meters"),
                "measurement_status": measurement_dict.get("status", "SUCCESS")
            })

        repo.add_features(file_id, features_to_save)
        repo.update_file_status(file_id, "COMPLETED")

        updated_record = repo.get_file_by_id(file_id)
        return updated_record

    except HTTPException:
        raise
    except ValueError as val_err:
        logger.error(f"Validation error during file processing: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        logger.exception("Unexpected error processing geospatial file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the geospatial file: {str(exc)}"
        )

@router.get("/", response_model=FileListResponse)
def list_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db_connection)
):
    """
    Lists all uploaded geospatial files with pagination.
    """
    repo = GeospatialRepository(conn)
    total, files = repo.list_files(skip=skip, limit=limit)
    return FileListResponse(total=total, files=files)

@router.get("/{file_id}/", response_model=FileInfoResponse)
def get_file_info(
    file_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection)
):
    """
    Returns metadata information for a specific uploaded file by ID.
    """
    repo = GeospatialRepository(conn)
    file_record = repo.get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{file_id}' not found."
        )
    return file_record

@router.get("/{file_id}/measurements/", response_model=FileMeasurementsResponse)
def get_file_measurements(
    file_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection)
):
    """
    Returns detailed measurement information for all features within an uploaded file.
    Includes feature geometries, attributes, calculated areas/lengths, projected CRS, and summary metrics.
    """
    repo = GeospatialRepository(conn)
    file_record = repo.get_file_by_id(file_id)
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{file_id}' not found."
        )

    features_db = repo.get_features_by_file_id(file_id)

    total_features = len(features_db)
    polygon_count = 0
    linestring_count = 0
    point_count = 0
    unsupported_count = 0
    total_area_sq_m = 0.0
    total_length_m = 0.0

    features_response: List[FeatureResponse] = []

    for feat in features_db:
        gtype = feat["geometry_type"]
        area_val = feat.get("area_sq_m")
        length_val = feat.get("length_m")

        if gtype in ["Polygon", "MultiPolygon"]:
            polygon_count += 1
            if area_val is not None:
                total_area_sq_m += area_val
        elif gtype in ["LineString", "MultiLineString"]:
            linestring_count += 1
            if length_val is not None:
                total_length_m += length_val
        elif gtype in ["Point", "MultiPoint"]:
            point_count += 1
        else:
            unsupported_count += 1

        meas_detail = MeasurementDetail(
            area_sq_m=area_val,
            area_hectares=feat.get("area_hectares"),
            area_sq_km=feat.get("area_sq_km"),
            length_m=length_val,
            length_km=feat.get("length_km"),
            unit=feat.get("measurement_unit", "meters"),
            status=feat.get("measurement_status", "SUCCESS")
        )

        features_response.append(
            FeatureResponse(
                feature_id=feat["feature_index"],
                geometry_type=gtype,
                crs_projected=feat.get("crs_projected"),
                properties=feat.get("properties") or {},
                measurements=meas_detail,
                geometry=feat["geometry"]
            )
        )

    summary = MeasurementSummary(
        total_features=total_features,
        polygon_count=polygon_count,
        linestring_count=linestring_count,
        point_count=point_count,
        unsupported_count=unsupported_count,
        total_area_sq_m=round(total_area_sq_m, 4),
        total_area_hectares=round(total_area_sq_m / 10000.0, 6),
        total_length_m=round(total_length_m, 4)
    )

    return FileMeasurementsResponse(
        file_id=file_record["id"],
        filename=file_record["filename"],
        feature_count=file_record["feature_count"],
        crs_original=file_record["crs"],
        status=file_record["status"],
        summary=summary,
        features=features_response
    )

@router.delete("/{file_id}/", status_code=status.HTTP_200_OK)
def delete_file(
    file_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection)
):
    """
    Deletes a geospatial file and its associated feature records.
    """
    repo = GeospatialRepository(conn)
    deleted = repo.delete_file(file_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{file_id}' not found."
        )
    return {"message": f"Geospatial file '{file_id}' and all feature records successfully deleted."}
