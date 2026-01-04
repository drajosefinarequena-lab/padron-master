import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher

# Configuración
st.set_page_config(page_title="Limpieza T3F", layout="wide", page_icon="🧹")
st.title("🧹 Centro de Comando y Limpieza - T3F")

# --- 1. CARGA DE DATOS BLINDADA ---
@st.cache_data(ttl=60) # ttl=60 hace que se refresque cada 60 segundos (evita caché viejo)
def cargar_datos():
    # A. Cargar Padrón Sucio
    try:
        df = pd.read_csv("datos.csv", encoding='latin-1', sep=None, engine='python')
    except FileNotFoundError:
        return None, {}

    # B. Cargar Diccionario de Correcciones
    diccionario = {}
    try:
        # Intentamos leer detectando automáticamente el separador (; o ,)
        # Asumimos que NO tiene encabezados si fallan los nombres, o leemos la primera columna como 'Mal' y la segunda como 'Bien'
        df_corr = pd.read_csv("correcciones.csv", encoding='latin-1', sep=None, engine='python', header=None)
        
        # Si el archivo tiene títulos como "Original, Corregido", la primera fila sobra.
        # Verificamos si la primera fila parece un encabezado
        first_row = df_corr.iloc[0].astype(str).str.lower().tolist()
        if "original" in first_row or "mal" in first_row:
            df_corr = df_corr[1:] # Borramos la primera fila
            
        # Convertimos a diccionario
        # Columna 0 = Lo que está Mal (Gardel Carlos)
        # Columna 1 = Lo que está Bien (Carlos Gardel)
        diccionario = dict(zip(df_corr.iloc[:,0].astype(str).str.upper().str.strip(), 
                               df_corr.iloc[:,1].astype(str).str.upper().str.strip()))
        
    except Exception as e:
        st.sidebar.error(f"Error leyendo correcciones.csv: {e}")
        diccionario = {} 
    
    return df, diccionario

# --- 2. MOTOR DE LIMPIEZA ---
def normalizar_calle(texto, diccionario_externo):
    if not isinstance(texto, str): return ""
    calle = texto.upper().strip()
    
    # Prioridad 1: Archivo de correcciones (BÚSQUEDA EXACTA)
    if calle in diccionario_externo:
        return diccionario_externo[calle]
    
    # Prioridad 2: Reglas Fijas
    fijas = {
        "AV SAN MARTIN": "AV SAN MARTIN", "AV. SAN MARTIN": "AV SAN MARTIN",
        "BOULEVARD SAN MARTIN": "BOULEVARD SAN MARTIN",
        "GLADIOLO": "DE LOS GLADIOLOS", "LOS GLADIOLOS": "DE LOS GLADIOLOS",
        "E DE LOS ANDES": "EJERCITO DE LOS ANDES",
        "ANCHORDOQUY": "DR ENRIQUE ANCHORDOQUI", "ANCHORDOQUI": "DR ENRIQUE ANCHORDOQUI"
    }
    if calle in fijas: return fijas[calle]
        
    # Prioridad 3: Limpieza General
    basura = ["AV.", "AV ", "CALLE ", "DR.", "DR ", "GRAL.", "GRAL ", "PJE ", "PJE."]
    calle_limpia = calle
    for b in basura:
        if calle_limpia.startswith(b):
            calle_limpia = calle_limpia.replace(b, "")
            
    return calle_limpia.strip()

def extraer_direccion(texto, diccionario):
    if not isinstance(texto, str): return None, None, None
    match = re.search(r"^([A-Z\s\.\d\(\)\-\/ñÑ]+?)\s+(\d+)", texto.upper())
    if match:
        raw = match.group(1).strip()
        altura = int(match.group(2))
        clean = normalizar_calle(raw, diccionario)
        return raw, altura, clean
    return None, None, None

# --- INICIO APP ---
df, diccionario_correcciones = cargar_datos()

# --- DIAGNÓSTICO LATERAL (AQUÍ VERÁS SI SE CARGÓ BIEN) ---
st.sidebar.header("🔍 Diagnóstico")
if diccionario_correcciones:
    st.sidebar.success(f"Reglas cargadas: {len(diccionario_correcciones)}")
    
    # Buscador para verificar si tu regla está activa
    test = st.sidebar.text_input("Prueba una corrección (Ej: C GARDEL)").upper()
    if test:
        if test in diccionario_correcciones:
            st.sidebar.success(f"✅ ¡La tengo! \n{test} -> {diccionario_correcciones[test]}")
        else:
            st.sidebar.error("❌ No encuentro esa regla en el archivo.")
            st.sidebar.markdown("**Contenido de las primeras 5 reglas leídas:**")
            st.sidebar.write(list(diccionario_correcciones.items())[:5])
else:
    st.sidebar.warning("No se detectaron reglas en correcciones.csv")

if df is not None:
    # Procesamos
    if 'CALLE_LIMPIA' not in df.columns:
        with st.spinner('Limpiando base...'):
            datos = df['Domicilio'].apply(lambda x: pd.Series(extraer_direccion(x, diccionario_correcciones)))
            df['CALLE_ORIGINAL'] = datos[0]
            df['ALTURA'] = datos[1]
            df['CALLE_LIMPIA'] = datos[2]
            df = df.dropna(subset=['CALLE_LIMPIA'])

    st.success(f"Base de Datos Activa: {len(df)} registros.")
    
    tab1, tab2 = st.tabs(["🔍 VERIFICAR RESULTADOS", "🛠️ GENERAR NUEVAS REGLAS"])
    
    with tab1:
        col1, col2 = st.columns([2,1])
        with col1:
            modo = st.radio("Ver por:", ["Calle Limpia", "Persona"], horizontal=True)
        
        if modo == "Calle Limpia":
            calles = sorted(df['CALLE_LIMPIA'].unique())
            c = st.selectbox("Selecciona Calle:", calles)
            if c:
                f = df[df['CALLE_LIMPIA'] == c]
                # Mostramos la columna ORIGINAL para que veas que se unificaron
                st.write(f"Afiliados en **{c}**: {len(f)}")
                st.dataframe(f[['Apellido', 'Nombre', 'CALLE_ORIGINAL', 'ALTURA']].sort_values('ALTURA'))
        else:
            b = st.text_input("Apellido:")
            if b:
                st.dataframe(df[df['Apellido'].str.contains(b.upper(), na=False)])

    with tab2:
        st.header("Generador de Reglas")
        if st.button("🔎 Buscar errores pendientes"):
            with st.spinner("Analizando..."):
                calles_unicas = sorted(df['CALLE_ORIGINAL'].unique().astype(str))
                sugerencias = []
                procesados = set()
                
                def clean_tmp(t):
                    for p in ["AV.", "AV ", "CALLE ", "DR.", "DR "]: t = t.replace(p, "")
                    return t.strip()

                progress = st.progress(0)
                for i, calle_a in enumerate(calles_unicas):
                    if i % 100 == 0: progress.progress(i/len(calles_unicas))
                    
                    # IGNORAR SI YA ESTÁ CORREGIDA
                    if calle_a in diccionario_correcciones: continue
                    
                    if calle_a in procesados: continue
                    nm_a = clean_tmp(calle_a)
                    grupo = [calle_a]
                    
                    for calle_b in calles_unicas:
                        if calle_b in diccionario_correcciones: continue
                        if calle_a == calle_b or calle_b in procesados: continue
                        if SequenceMatcher(None, nm_a, clean_tmp(calle_b)).ratio() > 0.85:
                            grupo.append(calle_b)
                            procesados.add(calle_b)
                    
                    if len(grupo) > 1:
                        procesados.add(calle_a)
                        oficial = normalizar_calle(grupo[0], diccionario_correcciones)
                        for mala in grupo:
                            if mala not in diccionario_correcciones and mala != oficial:
                                sugerencias.append({"Original": mala, "Corregido": oficial})
                
                progress.empty()
                if sugerencias:
                    df_sug = pd.DataFrame(sugerencias)
                    st.warning(f"⚠️ {len(df_sug)} nuevos errores.")
                    st.dataframe(df_sug)
                    csv_nuevo = df_sug.to_csv(index=False, header=False).encode('utf-8')
                    st.download_button("⬇️ Descargar nuevos", csv_nuevo, "nuevos_errores.csv", "text/csv")
                else:
                    st.success("¡Todo limpio!")

else:
    st.warning("Sube datos.csv")
