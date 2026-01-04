import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher

# Configuración
st.set_page_config(page_title="Limpieza T3F", layout="wide", page_icon="🧹")
st.title("🧹 Centro de Comando y Limpieza - T3F")

# --- 1. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    # A. Cargar Padrón Sucio
    try:
        # Intenta leer CSV con coma, si falla prueba punto y coma
        df = pd.read_csv("datos.csv", encoding='latin-1', sep=',')
        if df.shape[1] < 2: df = pd.read_csv("datos.csv", encoding='latin-1', sep=';')
    except FileNotFoundError:
        return None, None

    # B. Cargar Diccionario de Correcciones (Si existe en GitHub)
    try:
        df_corr = pd.read_csv("correcciones.csv")
        # Creamos un diccionario Python: { "Nombre Mal": "Nombre Bien" }
        diccionario = dict(zip(df_corr.iloc[:,0], df_corr.iloc[:,1]))
    except:
        diccionario = {} # Si no existe el archivo, usamos diccionario vacío
    
    return df, diccionario

# --- 2. MOTOR DE LIMPIEZA ---
def normalizar_calle(texto, diccionario_externo):
    if not isinstance(texto, str): return ""
    calle = texto.upper().strip()
    
    # Prioridad 1: Archivo de correcciones
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
    match = re.search(r"^([A-Z\s\.\d\(\)\-\/]+?)\s+(\d+)", texto.upper())
    if match:
        raw = match.group(1).strip()
        altura = int(match.group(2))
        clean = normalizar_calle(raw, diccionario)
        return raw, altura, clean
    return None, None, None

# --- INICIO APP ---
df, diccionario_correcciones = cargar_datos()

if df is not None:
    # Procesamos en memoria
    if 'CALLE_LIMPIA' not in df.columns:
        with st.spinner('Aplicando reglas de limpieza a toda la base...'):
            datos = df['Domicilio'].apply(lambda x: pd.Series(extraer_direccion(x, diccionario_correcciones)))
            df['CALLE_ORIGINAL'] = datos[0]
            df['ALTURA'] = datos[1]
            df['CALLE_LIMPIA'] = datos[2]
            df = df.dropna(subset=['CALLE_LIMPIA'])

    st.success(f"✅ Base Activa: {len(df)} registros. (Correcciones externas aplicadas: {len(diccionario_correcciones)})")
    
    tab1, tab2 = st.tabs(["🔍 PRUEBA DE BÚSQUEDA", "🛠️ HERRAMIENTA DE LIMPIEZA"])
    
    # --- PESTAÑA 1: PARA VER CÓMO QUEDA ---
    with tab1:
        col1, col2 = st.columns([2,1])
        with col1:
            modo = st.radio("Buscar por:", ["Calle", "Persona"], horizontal=True)
        
        if modo == "Calle":
            calles = sorted(df['CALLE_LIMPIA'].unique())
            c = st.selectbox("Selecciona una calle ya limpia:", calles)
            if c:
                f = df[df['CALLE_LIMPIA'] == c]
                st.write(f"Vecinos en **{c}**: {len(f)}")
                st.dataframe(f[['Apellido', 'Nombre', 'CALLE_LIMPIA', 'CALLE_ORIGINAL', 'ALTURA']].sort_values('ALTURA'))
        else:
            b = st.text_input("Apellido:")
            if b:
                st.dataframe(df[df['Apellido'].str.contains(b.upper(), na=False)])

    # --- PESTAÑA 2: PARA GENERAR EL ARCHIVO DE CORRECCIONES ---
    with tab2:
        st.header("Generador de Reglas")
        st.markdown("Esta herramienta busca nombres parecidos y crea el archivo para corregirlos.")
        
        if st.button("🔎 Buscar duplicados (Takes time)"):
            with st.spinner("Analizando similitudes..."):
                calles_unicas = sorted(df['CALLE_ORIGINAL'].unique().astype(str))
                sugerencias = []
                procesados = set()
                
                def clean_tmp(t):
                    for p in ["AV.", "AV ", "CALLE ", "DR.", "DR "]: t = t.replace(p, "")
                    return t.strip()

                progress = st.progress(0)
                for i, calle_a in enumerate(calles_unicas):
                    if i % 100 == 0: progress.progress(i/len(calles_unicas))
                    if calle_a in procesados: continue
                    nm_a = clean_tmp(calle_a)
                    grupo = [calle_a]
                    
                    for calle_b in calles_unicas:
                        if calle_a == calle_b or calle_b in procesados: continue
                        if SequenceMatcher(None, nm_a, clean_tmp(calle_b)).ratio() > 0.85:
                            grupo.append(calle_b)
                            procesados.add(calle_b)
                    
                    if len(grupo) > 1:
                        procesados.add(calle_a)
                        # Sugerimos usar la versión limpia automática como oficial
                        oficial = normalizar_calle(grupo[0], diccionario_correcciones)
                        for mala in grupo:
                            if mala != oficial:
                                sugerencias.append({"Original": mala, "Corregido": oficial})
                
                progress.empty()
                df_sug = pd.DataFrame(sugerencias)
                st.success(f"Se encontraron {len(df_sug)} correcciones sugeridas.")
                st.dataframe(df_sug)
                
                csv = df_sug.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Descargar correcciones.csv", csv, "correcciones.csv", "text/csv")
                st.info("Instrucciones: Descarga -> Revisa en Excel -> Sube a este repositorio en GitHub.")

else:
    st.warning("⚠️ Esperando archivo 'datos.csv'. Súbelo a GitHub.")
