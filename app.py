import streamlit as st
import folium
import pandas as pd
import plotly.express as px
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from services.data_client import get_comuna_context

# Configuración de Streamlit
st.set_page_config(page_title="GeoMed - Inteligencia Territorial", layout="wide", page_icon="🌍")

# Inyectar CSS Avanzado (UX/UI Premium B2B - Glassmorphism)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif;
        background-color: #030712;
        color: #E2E8F0;
    }
    
    /* Fondo con gradiente profundo */
    .stApp {
        background: radial-gradient(circle at top right, #0d1e3a, #030712 80%);
    }

    /* Glassmorphism Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
        margin-bottom: 1.2rem;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .metric-card:hover {
        transform: translateY(-8px);
        border: 1px solid rgba(1, 255, 132, 0.5);
        background: rgba(255, 255, 255, 0.05) !important;
    }
    
    h1, h2, h3 {
        font-weight: 800 !important;
        letter-spacing: -1.5px !important;
        color: #F8FAFC !important;
        text-shadow: 0 0 20px rgba(1, 255, 132, 0.2);
    }
    
    /* Pestañas (Tabs) Estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: rgba(255, 255, 255, 0.02);
        padding: 10px;
        border-radius: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 12px !important;
        color: #94A3B8 !important;
        padding: 10px 25px !important;
        border: 1px solid transparent !important;
        transition: 0.3s;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(1, 255, 132, 0.1) !important;
        color: #01FF84 !important;
        border: 1px solid rgba(1, 255, 132, 0.3) !important;
        box-shadow: 0 0 15px rgba(1, 255, 132, 0.1);
    }

    /* Botones Neón */
    .stButton>button {
        background: linear-gradient(90deg, #008751 0%, #01FF84 100%) !important;
        color: white !important;
        border: none !important;
        padding: 1rem 2rem !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        box-shadow: 0 8px 25px rgba(1, 255, 132, 0.2) !important;
        transition: all 0.4s !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button:hover {
        box-shadow: 0 12px 35px rgba(1, 255, 132, 0.4) !important;
        transform: translateY(-3px) scale(1.01);
    }

    /* Scrollbars Custom */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(1, 255, 132, 0.3); }

    /* Fix para prevenir que se corten las letras */
    * { line-height: 1.5; }
    div[data-testid="stMarkdownContainer"] p {
        overflow-wrap: break-word;
        word-wrap: break-word;
        hyphens: auto;
    }
    
    /* Contenedor de IA con borde neón */
    .st-emotion-cache-12w0qpk { border-radius: 20px; } /* Streamlit internal class for containers */

    /* Ocultar Menú superior, logo de GitHub y botón Deploy */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {visibility: hidden !important;}

    /* Forzar visibilidad y color del botón del panel lateral (flechita) */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 999999 !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        padding: 5px !important;
    }
    [data-testid="collapsedControl"] svg {
        fill: #01FF84 !important;
        color: #01FF84 !important;
    }
</style>
""", unsafe_allow_html=True)

# Cargar variables de entorno (Resiliencia Local + Cloud)
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

# Si no hay clave local, intentar buscar en los secretos de Streamlit (Cloud)
if not api_key:
    try:
        if "OPENROUTER_API_KEY" in st.secrets:
            api_key = st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        api_key = None

# Configuración de OpenRouter (Estabilizado con Cache de Recursos)
@st.cache_resource
def get_ai_client(_api_key):
    if not _api_key:
        return None
    try:
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=_api_key,
        )
    except Exception as e:
        st.error(f"Error inicializando OpenRouter: {e}")
        return None

client = get_ai_client(api_key)
# Lista de modelos para redundancia (Resiliencia en Hackathon)
MODELS = ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-12b-it:free"]
MODEL_NAME = MODELS[0]

        
# Función para generar contenido via OpenRouter con redundancia
def generate_ai_content(prompt, system_instruction):
    if not client: return "Error: Cliente AI no configurado."
    
    last_error = ""
    for model_id in MODELS:
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                continue # Intentar con el siguiente modelo si hay rate limit
            return f"Error en generación: {last_error}"
            
    return f"Todos los modelos gratuitos están saturados. Intenta de nuevo en unos segundos. (Detalle: {last_error})"

if "messages" not in st.session_state: st.session_state.messages = []
if "radar_insight" not in st.session_state: st.session_state.radar_insight = None
if "last_sim" not in st.session_state: st.session_state.last_sim = None

# --- CARGAS DE DATOS (REPROYECTADOS WGS84) ---
@st.cache_data
def load_comunas():
    path = "data/wgs84_limite_catastral_de_comun.geojson"
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

@st.cache_data
def load_barrios():
    path = "data/wgs84_limite_barrio_vereda_cata.geojson"
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

# Cargar POIs (Establecimientos) - Optimizado con Parquet (443k registros en milisegundos)
@st.cache_data
def load_poi_database():
    path = "data/pois.parquet"
    if not os.path.exists(path): return pd.DataFrame(columns=['lat', 'lon', 'nombre', 'comuna', 'sector'])
    return pd.read_parquet(path)

# Cargar GeoJSON de Metro (Local Reproyectado)
@st.cache_data
def load_metro_geojson():
    path = "data/wgs84_Estaciones_Sistema_Metro.geojson"
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

# Cargar Atractivos Turísticos
@st.cache_data
def load_attractions():
    path = "data/wgs84_atractivos_turisticos.geojson"
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

# Cargar Puntos Info Turística
@st.cache_data
def load_tur_info():
    path = "data/wgs84_puntos_de_informacion_tur.geojson"
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def filter_df_by_comuna(df, comuna_id):
    if not isinstance(df, pd.DataFrame) or df.empty or not comuna_id:
        return pd.DataFrame(columns=['lat', 'lon', 'nombre', 'comuna', 'sector'])
    
    target_id = str(comuna_id).strip().lstrip('0')
    if target_id == "": target_id = "0"
    
    mask = df['comuna'].astype(str).str.strip().str.lstrip('0') == target_id
    return df[mask].copy()

def filter_geojson_by_comuna(features, comuna_id):
    if not features or not comuna_id:
        return []
    
    target_id = str(comuna_id).strip().lstrip('0')
    if target_id == "": target_id = "0"
    
    filtered = []
    for f in features:
        props = f.get('properties', {})
        val = props.get('comuna', props.get('cod_comuna', props.get('comuna_corregimiento', '')))
        cid = str(val).strip().lstrip('0')
        if cid == target_id:
            filtered.append(f)
    return filtered

# --- LÓGICA DE ANALYTICS (Optimizado con Pandas) ---

# Mapa de códigos a nombres reales (Basado en el sistema de Industria y Comercio de Medellín)
SECTOR_MAP = {
    "01": "Industrial 🏗️",
    "02": "Comercial 🛍️",
    "03": "Servicios 🛠️",
    "04": "Otras Actividades 📋",
    "05": "Construcción 🏗️"
}

# Mapa de categorías a sectores amigables para el filtro
def get_macro_sectores(df):
    if not isinstance(df, pd.DataFrame) or df.empty or 'sector' not in df.columns: return []
    # Filtrar valores None o vacíos
    raw_sectors = [str(s) for s in df['sector'].unique() if s is not None and str(s).strip() != "" and str(s).lower() != 'none']
    # Mapear a nombres reales
    named_sectors = sorted([SECTOR_MAP.get(s, f"Sector {s}") for s in raw_sectors])
    return named_sectors

def get_comuna_stats(df_comuna):
    if not isinstance(df_comuna, pd.DataFrame) or df_comuna.empty:
        return {
            "total": 0, 
            "top_cat": "N/A", 
            "dist": {}, 
            "chart_data": pd.DataFrame(columns=['Sector', 'Cantidad']),
            "df": df_comuna
        }
    
    # Aplicar mapeo a la columna de sector para visualización
    df_viz = df_comuna.copy()
    df_viz['sector_nombre'] = df_viz['sector'].map(lambda x: SECTOR_MAP.get(str(x), f"Sector {x}"))
    
    total = len(df_viz)
    top_cat = df_viz['sector_nombre'].mode().iloc[0] if not df_viz.empty else "N/A"
    
    # Preparar DataFrame para gráficos
    counts = df_viz['sector_nombre'].value_counts().head(10).reset_index()
    counts.columns = ['Sector', 'Cantidad']
    
    return {
        "total": total,
        "top_cat": top_cat,
        "dist": counts.set_index('Sector')['Cantidad'].to_dict(),
        "chart_data": counts,
        "df": df_viz
    }

# --- UI PRINCIPAL ---
def main():
    col_logo, col_title = st.columns([1, 10])
    with col_logo:
        # Usar un logo genérico o el emoji si el archivo no existe
        st.markdown("## 🌍")
    with col_title:
        st.markdown("<h1 style='margin-bottom:0;'>GeoMed Intelligence</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94A3B8; margin-top:0;'>Geointeligencia y Analítica para el Ecosistema de Medellín</p>", unsafe_allow_html=True)
    st.divider()

    # Cargar datos base
    geojson_comunas = load_comunas()
    all_pois_df = load_poi_database()
    all_barrios = load_barrios()
    metro_data = load_metro_geojson()
    attraction_data = load_attractions()
    tur_info_data = load_tur_info()

    # Sidebar / Panel de Control
    if 'comuna_id' not in st.session_state: st.session_state.comuna_id = "10" # La Candelaria por defecto
    
    comunas_lista = []
    cnombres = {}
    if geojson_comunas:
        for f in geojson_comunas['features']:
            props = f['properties']
            cid, cnom = str(props.get('comuna','')), props.get('nombre','...').title()
            comunas_lista.append({"id": cid, "nombre": cnom})
            cnombres[cid] = cnom
        comunas_lista = sorted(comunas_lista, key=lambda x: int(x['id']) if x['id'].isdigit() else 99)

    with st.sidebar:
        st.markdown("## ⚙️ Panel de Control")
        opciones = [c['id'] for c in comunas_lista]
        idx = opciones.index(st.session_state.comuna_id) if st.session_state.comuna_id in opciones else 0
        st.session_state.comuna_id = st.selectbox("Seleccione Comuna:", opciones, format_func=lambda x: f"C{x} - {cnombres.get(x, '')}", index=idx)
        
        # Filtro de Sectores
        all_sectors = get_macro_sectores(all_pois_df)
        selected_sectors = st.multiselect("Filtrar Sectores (POI):", all_sectors, help="Filtra los datos del mapa y analítica por categoría")
        
        if st.button("🧹 Limpiar Filtros", use_container_width=True):
            st.session_state.comuna_id = "10"
            st.rerun()

    # Filtrar datos de la comuna seleccionada (ULTRA RÁPIDO con Pandas)
    poi_comuna = filter_df_by_comuna(all_pois_df, st.session_state.comuna_id)
    
    # Si hay filtros de sector activados, revertir nombres a códigos para filtrar
    if selected_sectors and not poi_comuna.empty and 'sector' in poi_comuna.columns:
        REVERSE_MAP = {v: k for k, v in SECTOR_MAP.items()}
        selected_codes = [REVERSE_MAP.get(s, s) for s in selected_sectors]
        poi_comuna = poi_comuna[poi_comuna['sector'].isin(selected_codes)]
    
    # Verificar si el DataFrame resultante está vacío y loguear para debug visual
    if poi_comuna.empty and st.session_state.comuna_id and selected_sectors:
        st.sidebar.warning(f"⚠️ No hay comercios de '{', '.join(selected_sectors)}' en C{st.session_state.comuna_id}.")
        
    stats = get_comuna_stats(poi_comuna)

    # Tabs Principal (Expansión para Hackathon)
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Radar Territorial", "📊 Análisis BI", "🧪 Simulador Éxito", "💡 Consultoría IA"])
    # TAB 1: RADAR (MAPA)
    # --------------------------
    with tab1:
        # 1. Mapa Base (Ancho completo)
        # Crear mapa base con Estilo Dark (Esri World Dark Gray) para máxima compatibilidad
        m = folium.Map(location=[6.2442, -75.5812], zoom_start=12, tiles=None, max_zoom=20)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="🌃 Medellín Tech (Oscuro)",
            max_zoom=20,
            max_native_zoom=16,
            overlay=False,
            control=True
        ).add_to(m)
        
        # Capas del Mapa
        if geojson_comunas:
            folium.GeoJson(
                geojson_comunas, 
                name="🚩 Comunas de Medellín",
                style_function=lambda x: {'fillColor': '#01FF84', 'color': '#01FF84', 'weight': 1, 'fillOpacity': 0.05}, 
                highlight_function=lambda x: {'weight': 3, 'color': '#FFFFFF', 'fillOpacity': 0.2}, 
                tooltip=folium.GeoJsonTooltip(fields=['nombre','comuna'], aliases=['Comuna:','Cod:'])
            ).add_to(m)
        
        if st.session_state.comuna_id:
            if all_barrios:
                barrios_comuna = filter_geojson_by_comuna(all_barrios['features'], st.session_state.comuna_id)
                if barrios_comuna:
                    folium.GeoJson(
                        {"type":"FeatureCollection","features":barrios_comuna}, 
                        name="🏘️ Barrios Locales",
                        style_function=lambda x: {'color':'#FBBF24', 'weight':1, 'dashArray':'5,5', 'fillOpacity':0}, 
                        tooltip=folium.GeoJsonTooltip(fields=['nombre_barrio'], aliases=['Barrio-Vereda:'])
                    ).add_to(m)
            
            if not poi_comuna.empty:
                fg_pois = folium.FeatureGroup(name="🏪 Establecimientos (POIs)")
                cluster = MarkerCluster().add_to(fg_pois)
                df_map = poi_comuna.head(500)
                for _, row in df_map.iterrows():
                    folium.CircleMarker(location=[row['lat'], row['lon']], radius=3, color="#01FF84", fill=True, tooltip=f"<b>{row['nombre']}</b>").add_to(cluster)
                fg_pois.add_to(m)
                
                heat_data = poi_comuna[['lat', 'lon']].values.tolist()
                HeatMap(heat_data, name="🔥 Heatmap de Saturación", radius=15, blur=10, min_opacity=0.3).add_to(m)

        if metro_data:
            folium.GeoJson(
                metro_data,
                name="🚇 Estaciones de Metro",
                marker=folium.CircleMarker(radius=7, color='#FF1493', fill=True, fillOpacity=1, fill_color='#FFFFFF', weight=2),
                tooltip=folium.GeoJsonTooltip(fields=['label', 'linea'], aliases=['🚇 Estación:', 'Línea:'])
            ).add_to(m)

        if attraction_data:
            atr_filtrados = filter_geojson_by_comuna(attraction_data['features'], st.session_state.comuna_id) if st.session_state.comuna_id else attraction_data['features']
            if atr_filtrados:
                folium.GeoJson(
                    {"type":"FeatureCollection","features":atr_filtrados},
                    name="🌟 Atractivos Turísticos",
                    marker=folium.Marker(icon=folium.Icon(color='orange', icon='star')),
                    tooltip=folium.GeoJsonTooltip(fields=['nombre_sitio', 'tipo_atractivo'], aliases=['🌟 Atractivo:', 'Tipo:'])
                ).add_to(m)

        if tur_info_data:
            folium.GeoJson(
                tur_info_data,
                name="ℹ️ Info Turística",
                show=False,
                marker=folium.Marker(icon=folium.Icon(color='blue', icon='info-sign')),
                tooltip=folium.GeoJsonTooltip(fields=['sitio', 'direccion'], aliases=['ℹ️ Punto Info:', 'Dir:'])
            ).add_to(m)
        
        folium.LayerControl(collapsed=False, position='topright').add_to(m)
            
        map_event = st_folium(
            m, 
            width="100%", 
            height=550, 
            key="radar_medellin_v3", 
            returned_objects=["last_active_drawing"]
        )
        
        if map_event and map_event.get("last_active_drawing"):
            new_cid = str(map_event["last_active_drawing"]["properties"].get("comuna")).strip()
            if new_cid != st.session_state.comuna_id:
                st.session_state.comuna_id = new_cid
                st.rerun()

        # 2. Panel Inferior (Insights y Controles)
        st.divider()
        col_info, col_ai = st.columns([1, 2])
        
        with col_info:
            st.markdown("### 🗺️ Entorno Local")
            if st.session_state.comuna_id:
                st.markdown(f"<div class='metric-card'>📍 <b>Comuna {st.session_state.comuna_id}</b><br>{cnombres.get(st.session_state.comuna_id, '')}</div>", unsafe_allow_html=True)
                st.metric("Puntos Comerciales", f"{len(poi_comuna):,}")
                st.info("💡 Usa el mapa para explorar la densidad comercial y nodos de transporte.")

        with col_ai:
            if st.session_state.comuna_id:
                st.markdown("### 🌟 Inteligencia Territorial")
                if st.button("🚀 Generar Insights Estratégicos", use_container_width=True):
                    metro_cercano = filter_geojson_by_comuna(metro_data['features'], st.session_state.comuna_id) if metro_data else []
                    atr_cercanos = filter_geojson_by_comuna(attraction_data['features'], st.session_state.comuna_id) if attraction_data else []
                    inf_cercanos = filter_geojson_by_comuna(tur_info_data['features'], st.session_state.comuna_id) if tur_info_data else []
                    
                    extra = {
                        "metro": [m['properties'].get('label') for m in metro_cercano],
                        "atractivos_turisticos": [a['properties'].get('nombre_sitio') for a in atr_cercanos],
                        "puntos_info": [i['properties'].get('sitio') for i in inf_cercanos],
                        "conteo_comercios_actuales": len(poi_comuna) if not poi_comuna.empty else 0
                    }
                    
                    context = get_comuna_context(st.session_state.comuna_id, "Desconocida", extra_context=extra)
                    try:
                        with st.spinner("Analizando micro-entorno con IA..."):
                            SYSTEM_INSTRUCTION_RADAR = (
                                "Eres un Analista Senior de Desarrollo Económico y Turismo en Medellín. "
                                "Tu objetivo es identificar 'Huecos de Mercado' y oportunidades de negocio competitivas. "
                                "Analiza la cercanía a estaciones de Metro, atractivos turísticos, puntos de información y el mix de comercios. "
                                "Sugiere 3 ideas de negocio disruptivas. Sé muy profesional y usa datos para justificar."
                            )
                            res = generate_ai_content(f"Contexto Territorial Extendido: {json.dumps(context)}", SYSTEM_INSTRUCTION_RADAR)
                            st.session_state.radar_insight = res
                    except Exception as e:
                        st.warning("🏮 El motor analítico está saturado. Por favor, reintenta en unos segundos.")
                
                if st.session_state.radar_insight:
                    with st.container(height=350, border=True):
                        st.markdown(st.session_state.radar_insight)

    # --------------------------
    # TAB 2: ANALYTICS BI
    # --------------------------
    with tab2:
        if not st.session_state.comuna_id:
            st.warning("Seleccione una comuna en el Radar para ver las estadísticas.")
        elif stats:
            st.subheader(f"Dashboard de Inteligencia Comuna {st.session_state.comuna_id}")
            st.markdown(f"Análisis detallado de **{cnombres.get(st.session_state.comuna_id, '')}**")
            
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Establecimientos", f"{stats['total']:,}")
            with k2: st.metric("Sector Dominante", stats['top_cat'][:20] + "...")
            with k3: st.metric("Índice de Oportunidad", "Estratégico 📈")
            
            st.divider()
            
            c_left, c_right = st.columns([2, 1])
            with c_left:
                if not stats['chart_data'].empty and 'Cantidad' in stats['chart_data'].columns:
                    fig = px.bar(
                        stats['chart_data'], 
                        x='Cantidad', 
                        y='Sector', 
                        orientation='h', 
                        title="Concentración por Actividad Económica", 
                        color='Cantidad', 
                        color_continuous_scale='GnBu'
                    )
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', height=450)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos analíticos para los filtros seleccionados.")
            
            with c_right:
                st.markdown("### Mix de Mercado Local")
                if not stats['chart_data'].empty:
                    fig_pie = px.pie(stats['chart_data'].head(5), values='Cantidad', names='Sector', hole=0.4)
                    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', showlegend=False)
                    st.plotly_chart(fig_pie, use_container_width=True)
                    st.info("💡 Este mix sugiere la saturación actual. Las zonas con menor porcentaje representan nichos desatendidos.")

    # --------------------------
    # TAB 3: SIMULADOR DE ÉXITO (HACKATHON POWER-UP)
    # --------------------------
    with tab3:
        st.subheader("🧪 Simulador de Viabilidad Predictiva")
        st.markdown("Ingresa tu idea de negocio para recibir un análisis de riesgo y éxito basado en datos territoriales.")
        
        c_sim1, c_sim2 = st.columns([1, 1])
        with c_sim1:
            with st.container(border=True):
                idea = st.text_area("¿Cuál es tu propuesta de negocio?", placeholder="Ej: Venta de comida saludable cerca de la estación Estadio...", height=150)
                # Usamos la comuna global por defecto pero permitimos cambiarla para simular
                sim_comuna = st.selectbox("Comuna de Simulación:", opciones, format_func=lambda x: f"C{x} - {cnombres.get(x, '')}", key="sim_sel", index=idx)
                
                if st.button("🚀 Calcular Probabilidad de Éxito", use_container_width=True):
                    if idea:
                        p_sim = filter_df_by_comuna(all_pois_df, sim_comuna)
                        m_sim = filter_geojson_by_comuna(metro_data['features'], sim_comuna) if metro_data else []
                        
                        ctx_sim = {
                            "comuna": cnombres.get(sim_comuna, "Desconocida"),
                            "competencia_en_sector": len(p_sim),
                            "puntos_transporte": [m['properties'].get('label') for m in m_sim],
                            "top_actividades": p_sim['sector'].value_counts().head(5).to_dict() if not p_sim.empty and 'sector' in p_sim.columns else {}
                        }
                        
                        try:
                            with st.spinner("Consultando algoritmos de inteligencia territorial..."):
                                SYSTEM_INSTRUCTION_SIMULATOR = (
                                    "Eres el 'Algoritmo de Viabilidad DataMede'. Tu función es evaluar ideas de negocio en Medellín. "
                                    "Recibirás contexto de transporte, turismo y competencia. Debes dar un Score de Éxito del 0 al 100%. "
                                    "Sé crítico pero constructivo. Estructura tu respuesta así: "
                                    "1. 📈 SCORE DE ÉXITO: [X]% \n"
                                    "2. 🧩 ANÁLISIS DE ENTORNO: (Relación con Metro/Turismo/Competencia) \n"
                                    "3. ⚠️ RIESGOS DETECTADOS \n"
                                    "4. 💡 RECOMENDACIÓN DE IMPACTO."
                                )
                                sim_resp = generate_ai_content(f"NEGOCIO: {idea} | CONTEXTO: {json.dumps(ctx_sim)}", SYSTEM_INSTRUCTION_SIMULATOR)
                                st.session_state.last_sim = sim_resp
                        except Exception as e:
                            st.warning("⚠️ Error de cuota: El simulador está saturado. Reintenta en breve.")
                    else:
                        st.warning("Por favor, describe tu idea para realizar la simulación.")

        with c_sim2:
            if "last_sim" in st.session_state:
                st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
                st.markdown("### 📊 Resultado del Análisis")
                st.markdown(st.session_state.last_sim)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Botón de exportación simulado (Wow factor)
                st.download_button("📩 Descargar Reporte de Viabilidad (PDF)", "Contenido del reporte...", file_name="DataMede_Reporte.pdf", disabled=True, help="Función disponible en versión Pro")
            else:
                st.info("👈 Ingresa los detalles de tu emprendimiento para activar el motor de predicción.")

    # --------------------------
    # TAB 4: CONSULTORÍA IA
    # --------------------------
    with tab4:
        st.subheader("💡 Consultoría Estratégica en Tiempo Real")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("Pregúntale a DataMede sobre el mercado..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            if client:
                with st.chat_message("assistant"):
                    with st.spinner("Analizando..."):
                        SYSTEM_INSTRUCTION_CHATBOT = (
                            "Eres un Consultor Experto en Emprendimiento e Inteligencia Territorial en Medellín. "
                            "Ayudas a validar y mejorar ideas de negocio usando datos de transporte (Metro), turismo y competencia local."
                        )
                        full_prompt = f"Contexto Comuna {st.session_state.comuna_id}. Pregunta: {prompt}" if st.session_state.comuna_id else prompt
                        
                        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION_CHATBOT}]
                        for m in st.session_state.messages[:-1]:
                            messages.append({"role": m["role"], "content": m["content"]})
                        messages.append({"role": "user", "content": full_prompt})
                        
                        # Intentar usar el modelo principal con fallback manual para el chat
                        res_text = "Error: No se pudo obtener respuesta."
                        for m_id in MODELS:
                            try:
                                resp = client.chat.completions.create(
                                    model=m_id,
                                    messages=messages
                                )
                                res_text = resp.choices[0].message.content
                                break
                            except Exception as e:
                                if "429" in str(e): continue
                                res_text = f"Error: {e}"
                                break
                        st.markdown(res_text)
                        st.session_state.messages.append({"role": "assistant", "content": res_text})

if __name__ == "__main__": main()
