from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_file_id() -> str:
    return uuid.uuid4().hex[:12]

class GeospatialFile(Base):
    __tablename__ = "geospatial_files"

    id = Column(String(36), primary_key=True, default=generate_file_id)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'SHAPEFILE' or 'KML'
    file_size_bytes = Column(Integer, nullable=False, default=0)
    feature_count = Column(Integer, nullable=False, default=0)
    crs = Column(String(100), nullable=False, default="EPSG:4326")
    status = Column(String(50), nullable=False, default="PROCESSING")  # 'COMPLETED', 'FAILED', 'PROCESSING'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    features = relationship("FeatureRecord", back_populates="file", cascade="all, delete-orphan")

class FeatureRecord(Base):
    __tablename__ = "feature_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(36), ForeignKey("geospatial_files.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    geometry_type = Column(String(100), nullable=False)
    geometry = Column(JSON, nullable=False)
    properties = Column(JSON, nullable=False, default=dict)
    
    # Measurements calculated using projected CRS
    crs_projected = Column(String(100), nullable=True)
    area_sq_m = Column(Float, nullable=True)
    area_hectares = Column(Float, nullable=True)
    area_sq_km = Column(Float, nullable=True)
    length_m = Column(Float, nullable=True)
    length_km = Column(Float, nullable=True)
    measurement_unit = Column(String(50), nullable=False, default="meters")
    measurement_status = Column(String(50), nullable=False, default="SUCCESS")  # 'SUCCESS', 'NOT_APPLICABLE', 'UNSUPPORTED'
    
    file = relationship("GeospatialFile", back_populates="features")
