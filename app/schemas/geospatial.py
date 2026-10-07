from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class FileInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    feature_count: int
    crs: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

class MeasurementDetail(BaseModel):
    area_sq_m: Optional[float] = None
    area_hectares: Optional[float] = None
    area_sq_km: Optional[float] = None
    length_m: Optional[float] = None
    length_km: Optional[float] = None
    unit: str = "meters"
    status: str = "SUCCESS"  # SUCCESS, NOT_APPLICABLE, UNSUPPORTED
    note: Optional[str] = None

class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    feature_id: int = Field(..., alias="feature_index")
    geometry_type: str
    crs_projected: Optional[str] = None
    properties: Dict[str, Any]
    measurements: MeasurementDetail
    geometry: Dict[str, Any]

class MeasurementSummary(BaseModel):
    total_features: int
    polygon_count: int
    linestring_count: int
    point_count: int
    unsupported_count: int
    total_area_sq_m: float
    total_area_hectares: float
    total_length_m: float

class FileMeasurementsResponse(BaseModel):
    file_id: str
    filename: str
    feature_count: int
    crs_original: str
    status: str
    summary: MeasurementSummary
    features: List[FeatureResponse]

class FileListResponse(BaseModel):
    total: int
    files: List[FileInfoResponse]
