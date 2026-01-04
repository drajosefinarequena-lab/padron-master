import streamlit as st
import pandas as pd
import re
from difflib import get_close_matches

# Configuración
st.set_page_config(page_title="Limpieza Automática T3F", layout="wide", page_icon="🤖")
st.title("🤖 Padrón Inteligente T3F (Auto-Corrección)")

# --- 1. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv("datos.csv", encoding='latin-1', sep=None, engine='python')
    except:
        return None
    return df

# --- 2. EL CEREBRO DE AUTO-CORRECCIÓN ---
# Esta función decide cuál es el nombre correcto automáticamente
def auto_corregir(calle_sucia, lista_oficiales):
    if not isinstance(calle_sucia, str): return ""
    
    # 1. Limpieza básica para comparar mejor
    # Quitamos puntos y espacios extra
    sucia_norm = " ".join(calle_sucia.replace(".", " ").split())
    
    # 2. Intentamos buscar coincidencias cercanas en la lista oficial
    # cutoff=0.8 significa que deben coincidir al 80% (muy estricto para no equivocarse)
    coincidencias = get_close_matches(sucia_norm, lista_oficiales, n=1, cutoff=0.85)
    
    if coincidencias:
        return coincidencias[0] # Si encontró una muy parecida, devuelve la OFICIAL
    
    # 3. Lógica de inversión (GARDEL CARLOS -> CARLOS GARDEL)
    partes = sucia_norm.split()
    if len(partes) == 2:
        invertida = f"{partes[1]} {partes[0]}"
        coincidencias_inv = get_close_matches(invertida, lista_oficiales, n=1, cutoff=0.85)
        if coincidencias_inv:
            return coincidencias_inv[0]

    return sucia_norm # Si no encontró nada parecido, devuelve la original limpia

# --- 3. EXTRACCIÓN INICIAL ---
def extraer_calle_bruta(texto):
    if not isinstance(texto, str): return None
    # Regex para sacar solo el nombre antes del número
    match = re.search(r"^([A-Z\s\.\d\ñ\Ñ]+?)\s+(\d+)", texto.upper())
    if match:
        calle = match.group(1).strip()
        # Quitamos basura común SOLO para limpiar un poco antes de comparar
        for b in ["AV.", "AV ", "CALLE ", "DR.", "DR ", "GRAL.", "GRAL ", "PJE."]:
            if calle.startswith(b): calle = calle.replace(b, "")
        return calle.strip()
    return None

# --- INICIO APP ---
df = cargar_datos()

if df is not None:
    # PASO 1: Extraer nombres brutos
    if 'CALLE_BRUTA' not in df.columns:
        with st.spinner('Analizando estructura de direcciones...'):
            df['CALLE_BRUTA'] = df['Domicilio'].apply(extraer_calle_bruta)
            df = df.dropna(subset=['CALLE_BRUTA'])
            
            # PASO 2: CREAR LA LISTA "OFICIAL" AUTOMÁTICA
            # Asumimos que la versión "Correcta" es la que más se repite o la más larga
            # Aquí usamos un truco: contamos apariciones. Las calles bien escritas suelen ser mayoría.
            conteo = df['CALLE_BRUTA'].value_counts()
            # Tomamos solo las calles que aparecen al menos 5 veces como "referencia confiable"
            # Esto elimina errores de tipeo únicos (ej: "MIRTRE") de la lista de candidatos
            referentes = conteo[conteo > 2].index.tolist()
            
            # PASO 3: APLICAR AUTO-CORRECCIÓN A TODAS
            # Comparamos cada calle bruta contra la lista de referentes
            # Si "B MITRE" se parece a "BARTOLOME MITRE" (referente), se corrige sola.
            df['CALLE_OFICIAL'] = df['CALLE_BRUTA'].apply(lambda x: auto_corregir(x, referentes))
            
            # Extracción de altura para el mapa
            df['ALTURA'] = df['Domicilio'].str.extract(r'(\d+)').astype(float)

    st.success(f"✅ Padrón Auto-Corregido: {len(df)} registros.")
    
    # --- VISUALIZADOR DE RESULTADOS ---
    tab1, tab2 = st.tabs(["🗺️ BUSCADOR", "👁️ VERIFICAR CORRECCIONES"])
    
    with tab1:
        calles = sorted(df['CALLE_OFICIAL'].unique())
        calle_sel = st.selectbox("Selecciona Calle (Ya unificada):", calles)
        if calle_sel:
            f = df[df['CALLE_OFICIAL'] == calle_sel]
            st.write(f"Vecinos en **{calle_sel}**: {len(f)}")
            st.dataframe(f[['Apellido', 'Nombre', 'Domicilio', 'CALLE_OFICIAL']].sort_values('Domicilio'))
            
    with tab2:
        st.header("¿Qué hizo la IA?")
        st.write("Aquí puedes ver cómo agrupó las variantes automáticamente.")
        
        # Agrupamos para mostrar qué variantes terminaron en qué nombre oficial
        resumen = df.groupby('CALLE_OFICIAL')['CALLE_BRUTA'].unique().reset_index()
        # Filtramos solo las que agruparon más de 1 variante (donde hubo corrección)
        resumen['Variantes'] = resumen['CALLE_BRUTA'].apply(lambda x: len(x))
        resumen = resumen[resumen['Variantes'] > 1].sort_values('Variantes', ascending=False)
        
        st.dataframe(resumen[['CALLE_OFICIAL', 'CALLE_BRUTA']])

else:
    st.error("Sube datos.csv")
