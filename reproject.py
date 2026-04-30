import json
import os
from pyproj import Transformer

# Configuración de proyección: MAGNA-SIRGAS / Origen-Nacional (EPSG:9377) -> WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:9377", "EPSG:4326", always_xy=True)

def reproject_feature(feature):
    geom = feature.get("geometry")
    if not geom:
        return feature
    
    g_type = geom.get("type")
    coords = geom.get("coordinates")
    
    if g_type == "Point":
        # coords is [e, n]
        lon, lat = transformer.transform(coords[0], coords[1])
        geom["coordinates"] = [lon, lat]
    elif g_type == "Polygon":
        new_rings = []
        for ring in coords:
            new_ring = [list(transformer.transform(p[0], p[1])) for p in ring]
            new_rings.append(new_ring)
        geom["coordinates"] = new_rings
    elif g_type == "MultiPolygon":
        new_polys = []
        for poly in coords:
            new_poly = []
            for ring in poly:
                new_ring = [list(transformer.transform(p[0], p[1])) for p in ring]
                new_poly.append(new_ring)
            new_polys.append(new_poly)
        geom["coordinates"] = new_polys
    
    return feature

def process_file(input_path, output_path):
    print(f"Procesando {input_path}...")
    if not os.path.exists(input_path):
        print(f"Saltando {input_path} (no existe)")
        return
        
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "features" in data:
            data["features"] = [reproject_feature(f) for f in data["features"]]
        
        # Guardar con el mismo nombre pero marcando como WGS84 si fuera necesario
        # o simplemente sobreescribir la versión local para la app
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        print(f"¡Éxito! Guardado en {output_path}")
    except Exception as e:
        print(f"Error procesando {input_path}: {e}")

files = [
    "limite_catastral_de_comun.geojson",
    "limite_barrio_vereda_cata.geojson",
    "establecimientos_de_indus.geojson",
    "atractivos_turisticos.geojson",
    "puntos_de_informacion_tur.geojson",
    "Estaciones_Sistema_Metro.geojson"
]

def is_already_wgs84(feature):
    try:
        coords = feature['geometry']['coordinates']
        # If it's a point: [lon, lat]
        if isinstance(coords[0], float):
            return -180 <= coords[0] <= 180 and -90 <= coords[1] <= 90
        # If it's a polygon, check the first point
        while isinstance(coords[0], list):
            coords = coords[0]
        return -180 <= coords[0] <= 180 and -90 <= coords[1] <= 90
    except: return False

def reproject_feature_smart(feature):
    if is_already_wgs84(feature):
        return feature
    return reproject_feature(feature)

def process_file_smart(input_path, output_path):
    print(f"Procesando {input_path}...")
    if not os.path.exists(input_path): return
    try:
        with open(input_path, 'r', encoding='utf-8') as f: data = json.load(f)
        if "features" in data:
            data["features"] = [reproject_feature_smart(f) for f in data["features"]]
        with open(output_path, 'w', encoding='utf-8') as f: json.dump(data, f)
        print(f"¡Éxito! -> {output_path}")
    except Exception as e: print(f"Error: {e}")

for filename in files:
    in_p = os.path.join("data", filename)
    out_p = os.path.join("data", "wgs84_" + filename)
    process_file_smart(in_p, out_p)

