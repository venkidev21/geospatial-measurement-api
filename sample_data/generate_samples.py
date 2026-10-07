import os
import zipfile
import shapefile
from shapely.geometry import Polygon, LineString, Point, mapping

def generate_sample_kml(filepath: str):
    """Generates a sample KML file with Polygon, LineString, and Point placemarks."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Survey Site Alpha</name>
    <description>Sample geospatial survey containing polygon, line, and point features.</description>
    
    <!-- Feature 1: Central Park Polygon -->
    <Placemark>
      <name>Central City Park</name>
      <description>Urban green space zone</description>
      <ExtendedData>
        <Data name="zone_type"><value>Park</value></Data>
        <Data name="capacity"><value>5000</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5945,12.9716,0
              77.5995,12.9716,0
              77.5995,12.9766,0
              77.5945,12.9766,0
              77.5945,12.9716,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    
    <!-- Feature 2: Main Boulevard LineString -->
    <Placemark>
      <name>Grand Expressway</name>
      <description>Primary arterial highway corridor</description>
      <ExtendedData>
        <Data name="lanes"><value>4</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          77.5900,12.9700,0
          77.5950,12.9730,0
          77.6000,12.9780,0
        </coordinates>
      </LineString>
    </Placemark>
    
    <!-- Feature 3: Weather Monitoring Station Point -->
    <Placemark>
      <name>Weather Station #1</name>
      <description>Environmental telemetry sensor</description>
      <Point>
        <coordinates>77.5970,12.9740,15</coordinates>
      </Point>
    </Placemark>
    
  </Document>
</kml>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"Generated sample KML at: {filepath}")

def generate_sample_shapefile_zip(zip_filepath: str):
    """Generates a sample Shapefile .zip archive with polygon records and WGS84 projection."""
    temp_dir = os.path.dirname(zip_filepath)
    base_name = "land_use_survey"
    shp_path = os.path.join(temp_dir, f"{base_name}.shp")
    prj_path = os.path.join(temp_dir, f"{base_name}.prj")

    # Create Shapefile using pyshp
    w = shapefile.Writer(shp_path, shapeType=shapefile.POLYGON)
    w.field("NAME", "C", "50")
    w.field("CATEGORY", "C", "30")
    w.field("ID", "N", "10")

    # Polygon 1: Agricultural Parcel A
    poly1 = [
        [77.5800, 12.9600],
        [77.5850, 12.9600],
        [77.5850, 12.9650],
        [77.5800, 12.9650],
        [77.5800, 12.9600]
    ]
    w.poly([poly1])
    w.record("Agri Field A", "Agriculture", 101)

    # Polygon 2: Industrial Complex B
    poly2 = [
        [77.5860, 12.9600],
        [77.5900, 12.9600],
        [77.5900, 12.9640],
        [77.5860, 12.9640],
        [77.5860, 12.9600]
    ]
    w.poly([poly2])
    w.record("Industrial Tech Park", "Industrial", 102)

    w.close()

    # Create WGS84 .prj file (EPSG:4326 WKT string)
    wgs84_wkt = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    with open(prj_path, "w", encoding="utf-8") as f:
        f.write(wgs84_wkt)

    # Package into .zip file
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for ext in ['.shp', '.shx', '.dbf', '.prj']:
            file_to_add = os.path.join(temp_dir, f"{base_name}{ext}")
            zipf.write(file_to_add, arcname=f"{base_name}{ext}")
            os.remove(file_to_add)

    print(f"Generated sample Shapefile zip at: {zip_filepath}")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    generate_sample_kml(os.path.join(out_dir, "sample_survey.kml"))
    generate_sample_shapefile_zip(os.path.join(out_dir, "sample_shapefile.zip"))
