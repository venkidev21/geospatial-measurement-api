import re
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class KMLParser:
    @staticmethod
    def _strip_ns(tag: str) -> str:
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag

    @classmethod
    def _parse_coordinates(cls, coord_text: str) -> List[List[float]]:
        coords = []
        if not coord_text:
            return coords

        items = re.split(r'\s+', coord_text.strip())
        for item in items:
            if not item:
                continue
            parts = item.split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append([lon, lat])
                except ValueError:
                    continue
        return coords

    @classmethod
    def _parse_geometry_element(cls, elem: ET.Element) -> Optional[Dict[str, Any]]:
        tag = cls._strip_ns(elem.tag)

        if tag == "Point":
            coord_elem = None
            for child in elem:
                if cls._strip_ns(child.tag) == "coordinates":
                    coord_elem = child
                    break
            if coord_elem is not None and coord_elem.text:
                coords = cls._parse_coordinates(coord_elem.text)
                if coords:
                    return {"type": "Point", "coordinates": coords[0]}
            return None

        elif tag == "LineString":
            coord_elem = None
            for child in elem:
                if cls._strip_ns(child.tag) == "coordinates":
                    coord_elem = child
                    break
            if coord_elem is not None and coord_elem.text:
                coords = cls._parse_coordinates(coord_elem.text)
                if len(coords) >= 2:
                    return {"type": "LineString", "coordinates": coords}
            return None

        elif tag == "Polygon":
            outer_ring = None
            inner_rings = []

            for child in elem:
                child_tag = cls._strip_ns(child.tag)
                if child_tag == "outerBoundaryIs":
                    for ring in child:
                        if cls._strip_ns(ring.tag) == "LinearRing":
                            for ring_child in ring:
                                if cls._strip_ns(ring_child.tag) == "coordinates":
                                    if ring_child.text:
                                        outer_ring = cls._parse_coordinates(ring_child.text)
                elif child_tag == "innerBoundaryIs":
                    for ring in child:
                        if cls._strip_ns(ring.tag) == "LinearRing":
                            for ring_child in ring:
                                if cls._strip_ns(ring_child.tag) == "coordinates":
                                    if ring_child.text:
                                        hole_coords = cls._parse_coordinates(ring_child.text)
                                        if len(hole_coords) >= 3:
                                            inner_rings.append(hole_coords)

            if outer_ring and len(outer_ring) >= 3:
                poly_coords = [outer_ring] + inner_rings
                return {"type": "Polygon", "coordinates": poly_coords}
            return None

        elif tag == "MultiGeometry":
            geoms = []
            for child in elem:
                sub_geom = cls._parse_geometry_element(child)
                if sub_geom is not None:
                    geoms.append(sub_geom)
            
            if not geoms:
                return None
            
            if all(g["type"] == "Polygon" for g in geoms):
                multi_coords = [g["coordinates"] for g in geoms]
                return {"type": "MultiPolygon", "coordinates": multi_coords}
            elif all(g["type"] == "LineString" for g in geoms):
                multi_coords = [g["coordinates"] for g in geoms]
                return {"type": "MultiLineString", "coordinates": multi_coords}
            else:
                return {"type": "GeometryCollection", "geometries": geoms}

        return None

    @classmethod
    def _extract_properties(cls, placemark: ET.Element) -> Dict[str, Any]:
        props = {}
        for child in placemark:
            tag = cls._strip_ns(child.tag)
            if tag in ["name", "description"] and child.text:
                props[tag] = child.text.strip()
            elif tag == "ExtendedData":
                for ext_child in child:
                    ext_tag = cls._strip_ns(ext_child.tag)
                    if ext_tag == "Data":
                        name_attr = ext_child.attrib.get("name")
                        val_elem = None
                        for sub in ext_child:
                            if cls._strip_ns(sub.tag) == "value":
                                val_elem = sub
                                break
                        if name_attr and val_elem is not None and val_elem.text:
                            props[name_attr] = val_elem.text.strip()
                    elif ext_tag == "SchemaData":
                        for sd_child in ext_child:
                            if cls._strip_ns(sd_child.tag) == "SimpleData":
                                name_attr = sd_child.attrib.get("name")
                                if name_attr and sd_child.text:
                                    props[name_attr] = sd_child.text.strip()
        return props

    @classmethod
    def parse_kml(cls, kml_content_bytes: bytes) -> Tuple[List[Dict[str, Any]], str]:
        try:
            root = ET.fromstring(kml_content_bytes)
        except Exception as parse_err:
            raise ValueError(f"Invalid KML XML document: {parse_err}")

        features = []
        feature_index = 0

        for elem in root.iter():
            if cls._strip_ns(elem.tag) == "Placemark":
                props = cls._extract_properties(elem)
                
                geojson_geom = None
                for child in elem:
                    tag = cls._strip_ns(child.tag)
                    if tag in ["Point", "LineString", "Polygon", "MultiGeometry"]:
                        geojson_geom = cls._parse_geometry_element(child)
                        if geojson_geom is not None:
                            break

                if geojson_geom is not None:
                    features.append({
                        "feature_index": feature_index,
                        "geometry_geojson": geojson_geom,
                        "properties": props
                    })
                    feature_index += 1
                else:
                    logger.warning(f"Placemark at index {feature_index} has missing or empty geometry.")

        return features, "EPSG:4326"
