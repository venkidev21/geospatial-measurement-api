# Geospatial File Measurement API

FastAPI service for uploading geospatial vector files, extracting their features, and calculating metric area and length measurements after automatic UTM reprojection.

The API supports KML documents and Shapefile ZIP archives. Processed file metadata, feature attributes, geometries, CRS information, and measurements are persisted in SQLite for later retrieval.

## Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Technology](#technology)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Measurement Model](#measurement-model)
- [Testing](#testing)
- [Limitations](#limitations)

## Features

- Upload and process KML (`.kml` or `.xml`) files.
- Upload Shapefile archives as ZIP files containing the required Shapefile components.
- Extract geometries and feature attributes into a consistent GeoJSON-like representation.
- Select a UTM zone from feature coordinates and project geographic coordinates into meters.
- Calculate polygon and multipolygon area in square meters, hectares, and square kilometers.
- Calculate linestring and multilinestring length in meters and kilometers.
- Handle points as `NOT_APPLICABLE` and unsupported geometry types as `UNSUPPORTED`.
- Persist uploaded file records and feature measurements in SQLite.
- Browse the API through generated Swagger UI and ReDoc documentation.
- Run unit and integration tests with Pytest.

## How It Works

```text
Upload file
    -> Validate extension
    -> Parse geometries and attributes
    -> Determine source CRS
    -> Select the appropriate UTM zone
    -> Project coordinates into meters
    -> Calculate area and length
    -> Persist file and feature records
    -> Return structured JSON
```

The service does not calculate physical measurements directly from latitude/longitude values. Geographic coordinates are expressed in degrees, while the measurement engine works with projected metric coordinates.

For WGS 84 coordinates, the UTM zone is selected using the feature location:

```text
zone = floor((longitude + 180) / 6) + 1
```

The hemisphere determines the projected EPSG code: `EPSG:326xx` for the northern hemisphere and `EPSG:327xx` for the southern hemisphere.

## Technology

| Area | Technology |
| --- | --- |
| API framework | FastAPI |
| ASGI server | Uvicorn |
| Validation and schemas | Pydantic v2 |
| Configuration | pydantic-settings |
| Shapefile parsing | PyShp |
| KML parsing | Python standard-library XML parser |
| Projection | In-project Transverse Mercator implementation |
| Persistence | SQLite |
| Testing | Pytest and HTTPX |

## Project Structure

```text
.
├── app/
│   ├── main.py                         # FastAPI application and lifecycle
│   ├── config.py                       # Environment-backed settings
│   ├── database.py                     # SQLite connection and initialization
│   ├── api/
│   │   └── files.py                    # File and measurement endpoints
│   ├── models/
│   │   └── geospatial.py               # Persistence models
│   ├── repositories/
│   │   └── geospatial_repository.py   # Database access layer
│   ├── schemas/
│   │   └── geospatial.py               # Pydantic response schemas
│   └── services/
│       ├── crs_service.py              # CRS parsing and UTM selection
│       ├── kml_parser.py               # KML feature extraction
│       ├── measurement_service.py      # Projection and measurements
│       └── shapefile_parser.py         # Shapefile ZIP extraction
├── sample_data/
│   ├── generate_samples.py             # Sample-data generator
│   └── sample_survey.kml               # Example KML file
├── tests/
│   ├── conftest.py
│   ├── test_crs_measurements.py
│   ├── test_files_api.py
│   └── test_parsers.py
├── uploads/                            # Local upload workspace
├── pytest.ini
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Git

### Installation

```bash
git clone https://github.com/venkidev21/geospatial-measurement-api.git
cd geospatial-measurement-api

python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux or macOS
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

### Run the API

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The service is available at `http://127.0.0.1:8000`.

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/health`

## Configuration

The application reads settings from environment variables and can load them from a root-level `.env` file:

```env
PROJECT_NAME="Geospatial File Measurement API"
VERSION="1.0.0"
API_V1_STR="/api"
DATABASE_URL="sqlite:///./geospatial_api.db"
UPLOAD_DIR="./uploads"
MAX_UPLOAD_SIZE_MB=50
```

Do not commit `.env` files or credentials. Use a separate example file for shareable configuration.

## API Reference

All file endpoints are under `/api/files`.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/files/` | Upload and process a KML or Shapefile ZIP archive |
| `GET` | `/api/files/` | List processed files; supports `skip` and `limit` |
| `GET` | `/api/files/{file_id}/` | Retrieve file metadata and processing status |
| `GET` | `/api/files/{file_id}/measurements/` | Retrieve feature measurements and summary statistics |
| `DELETE` | `/api/files/{file_id}/` | Delete a file record and its feature records |
| `GET` | `/health` | Return service health and version information |

### Upload a file

```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -F "file=@sample_data/sample_survey.kml"
```

Example response:

```json
{
  "id": "e4a7b219c001",
  "filename": "sample_survey.kml",
  "file_type": "KML",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2026-10-07T12:00:00"
}
```

### Retrieve measurements

```bash
curl "http://127.0.0.1:8000/api/files/{file_id}/measurements/"
```

The response includes the original CRS, projected CRS per feature, source properties, GeoJSON-like geometry, individual measurements, and a summary:

```json
{
  "file_id": "e4a7b219c001",
  "filename": "sample_survey.kml",
  "feature_count": 3,
  "crs_original": "EPSG:4326",
  "status": "COMPLETED",
  "summary": {
    "total_features": 3,
    "polygon_count": 1,
    "linestring_count": 1,
    "point_count": 1,
    "unsupported_count": 0,
    "total_area_sq_m": 307221.8415,
    "total_area_hectares": 30.722184,
    "total_length_m": 1412.502
  },
  "features": []
}
```

The `features` array is abbreviated above. Each item contains `geometry_type`, `properties`, `geometry`, `crs_projected`, and a `measurements` object.

## Measurement Model

| Geometry | Measurement | Status |
| --- | --- | --- |
| `Polygon`, `MultiPolygon` | Area in square meters, hectares, and square kilometers | `SUCCESS` |
| `LineString`, `MultiLineString` | Length in meters and kilometers | `SUCCESS` |
| `Point`, `MultiPoint` | No area or length | `NOT_APPLICABLE` |
| Other geometry types | No measurement | `UNSUPPORTED` |

Polygon area accounts for interior rings. Line length is calculated from projected segment distances. Values are returned as numeric JSON fields; `null` is used where a measurement does not apply.

## Testing

Run the complete test suite from the repository root:

```bash
python -m pytest
```

The tests cover parser behavior, CRS and measurement calculations, upload validation, file listing, retrieval, and deletion workflows.

To generate or refresh sample data:

```bash
python sample_data/generate_samples.py
```

## Error Handling

- Unsupported extensions return `400 Bad Request`.
- Empty uploads return `400 Bad Request`.
- Unknown file IDs return `404 Not Found`.
- Unexpected processing failures return `500 Internal Server Error`.
- Invalid or unsupported geometries are represented in measurement status fields where possible instead of stopping the complete response.

## Limitations and Future Work

The current implementation is designed for local SQLite-backed processing. Potential next steps include:

- PostgreSQL/PostGIS support
- Authentication and authorization
- Object storage for uploaded files
- Background processing for large uploads
- Configurable CRS selection beyond automatic UTM
- Rate limiting and production deployment configuration
- A frontend map viewer for processed geometries

## License

Add the project license and copyright information here when the repository license is finalized.
