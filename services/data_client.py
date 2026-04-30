import os
import requests
import logging
from urllib.parse import urlencode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_from_api(url, comuna_id, fallback_data, params=None):
    if not url or url.strip() == "":
        return fallback_data
    
    try:
        response = requests.get(url, params=params, timeout=8)
        response.raise_for_status()
        
        data = response.json()
        if not data or len(data) == 0:
            return fallback_data
            
        # Retornamos solo un subset (ej. max 50 registros) para no sobrecargar el prompt
        if isinstance(data, list):
            return data[:50]
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.info(f"El endpoint {url} no fue encontrado (404). Usando fallback de resiliencia.")
        else:
            logger.warning(f"Error HTTP consumiendo {url}: {e.response.status_code}. Usando fallback.")
        return fallback_data
    except Exception as e:
        logger.warning(f"Error general consumiendo API {url}: {e}. Usando fallback.")
        return fallback_data

def fetch_estratificacion(comuna_id):
    """(GeoMedellín) WFS Server"""
    url = os.getenv("GEOMEDELLIN_ESTRATO_URL", "")
    fallback = {
        "origen": "Fallback",
        "estrato_predominante": "3" if comuna_id == "10" else "2" if comuna_id == "13" else "6",
        "descripcion": "Datos WFS simulados por timeout/CORS."
    }
    # Los servidores WFS son complejos de parametrizar por comuna en texto plano sin CQL_FILTER.
    # Aquí intentamos una petición básica si es posible, de lo contrario cae al fallback.
    return fetch_from_api(url, comuna_id, fallback, params={"request": "GetCapabilities", "service": "WFS"})

def fetch_pois(comuna_id):
    """(MEData) Establecimientos de Comercio Matriculados (Socrata)"""
    url = os.getenv("MEDATA_POI_URL", "")
    fallback = {
        "aviso": "Usando datos base",
        "comercios_principales": "Tiendas, Peluquerías, Restaurantes informales."
    }
    # Socrata: filtramos con un texto libre o campo general si no conocemos el nombre exacto de la comuna.
    # Usamos $q={comuna_id} para búsqueda general en toda la fila o limitamos
    return fetch_from_api(url, comuna_id, fallback, params={"$limit": 30, "$q": comuna_id})

def fetch_calidad_vida(comuna_id):
    """(MEData) Índice Calidad de Vida (Socrata)"""
    url = os.getenv("MEDATA_CALIDAD_VIDA_URL", "")
    fallback = {
        "aviso": "Usando estimación",
        "indice_calidad_vida": "Medio-Bajo"
    }
    return fetch_from_api(url, comuna_id, fallback, params={"$limit": 5, "$q": comuna_id})

def get_comuna_context(comuna_id, nombre_comuna, extra_context=None):
    """Recopila info al instante ('fetch' selectivo de innovación)."""
    return {
        "comuna": {
            "id": comuna_id,
            "nombre": nombre_comuna
        },
        "geometria_y_entorno_local": extra_context or {},
        "fuentes_en_vivo": {
            "censo_edificaciones_estrato": fetch_estratificacion(comuna_id),
            "puntos_de_interes_pois": fetch_pois(nombre_comuna),
            "encuesta_calidad_vida": fetch_calidad_vida(nombre_comuna)
        }
    }
