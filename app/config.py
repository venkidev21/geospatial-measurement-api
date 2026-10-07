import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    PROJECT_NAME: str = "Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database configuration
    DATABASE_URL: str = "sqlite:///./geospatial_api.db"
    
    # Upload storage directory
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
