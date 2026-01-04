import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher

# Configuración
st.set_page_config(page_title="Padrón Inteligente T3F", layout="wide", page_icon="🧠")
st.title("🧠 Padrón Inteligente: Normalización + Fuzzy Matching")

# --- 1. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    archivo = "datos_procesados - datos_procesados (1).csv"
    try:
        try:
            df = pd.read_csv(archivo, encoding='latin-1')
        except:
            df = pd.read_csv(archivo, encoding='utf-8')
        
        # Normalizar columnas
        df.columns = [c.upper().strip() for c in df.columns]
        return df
    except FileNotFoundError:
        st.error(f"❌ No encuentro el archivo: {archivo}")
        return None

# --- 2. TRADUCTOR DE ABREVIATURAS Y NÚMEROS ---
def expandir_abreviaturas(texto):
    if not isinstance(texto, str): return ""
    
    # Normalización básica
    calle = texto.upper().strip()
    calle = re.sub(r"[.]", " ", calle) # Quitar puntos: DR. -> DR
    calle = re.sub(r"\s+", " ", calle) # Quitar espacios dobles
    
    # DICCIONARIO DE ABREVIATURAS MILITARES Y PROFESIONALES
    reemplazos = {
        r"\bSGTO\b": "SARGENTO",
        r"\bDR\b": "DOCTOR",
        r"\bDOC\b": "DOCTOR",
        r"\bDRA\b": "DOCTORA",
        r"\bGRAL\b": "GENERAL",
        r"\bCNEL\b": "CORONEL",
        r"\bTTE\b": "TENIENTE",
        r"\bSUBTTE\b": "SUBTENIENTE",
        r"\bALMTE\b": "ALMIRANTE",
        r"\bCDTE\b": "COMANDANTE",
        r"\bPROF\b": "PROFESOR",
        r"\bING\b": "INGENIERO",      # <--- AQUÍ ESTABA EL ERROR, YA CORREGIDO
        r"\bARQ\b": "ARQUITECTO",
        r"\bPBR\b": "PRESBITERO",
        r"\bPCIA\b": "PROVINCIA",
        r"\bLIB\b": "LIBERTADOR",
        r"\bAV\b": "AVENIDA", 
        r"\bAVDA\b": "AVENIDA",
        r"\bBV\b": "BOULEVARD",
        r"\bPJE\b": "PASAJE",
    }
    
    for patron, reemplazo in reemplazos.items():
        calle = re.sub(patron, reemplazo, calle)

    # REGLAS ESPECÍFICAS DE "R" (RIO, RUTA, ETC)
    # R JACHAL -> RIO JACHAL
    calle = re.sub(r"\bR\s+(JACHAL|CUARTO|NEGRO|SALADO|DIAMANTE|TERCERO)\b", r"RIO \1", calle)
    
    # NÚMEROS ROMANOS Y VARIANTES NUMÉRICAS
    # RIO 4 / RIO IV -> RIO CUARTO
    calle = re.sub(r"\bRIO\s+(4|IV)\b", "RIO CUARTO", calle)
    calle = re.sub(r"\bRIO\s+(3|III)\b", "RIO TERCERO", calle)
    
    # 1 DE MAYO (Unificar I DE MAYO, 1RO DE MAYO)
    calle = re.sub(r"\b(1RO|1|I)\s+DE\s+MAYO\b", "1 DE MAYO", calle)
    
    # 3 DE FEBRERO
    calle = re.sub(r"\b(3|III)\s+DE\s+FEBRERO\b", "3 DE FEBRERO", calle)

    # ARREGLOS DE SANTOS (Reciclado del paso anterior)
    calle = re.sub(r"\b(STA|S)\s+RITA\b", "SANTA RITA", calle)
    calle = re.sub(r"\b(STO|S)\s+IGNACIO\b", "SAN IGNACIO", calle)
    calle = re.sub(r"\b(STA|S)\s+MARIA\b", "SANTA MARIA", calle)
    calle = re.sub(r"\b(STO|S)\s+MARTIN\b", "SAN MARTIN", calle)

    return calle.strip()

# --- 3. FUZZY MATCHING (El Unificador Inteligente) ---
def generar_mapa_fuzzy(lista_calles_unicas, umbral=0.70):
    """
    Agrupa calles similares basándose en similitud de texto.
    """
    calles_ordenadas = sorted(lista_calles_unicas)
    mapa_correccion = {}
    procesados = set()
    
    # Barra de progreso visual
    texto_progreso = st.empty()
    progreso = st.progress(0)
    total = len(calles_ordenadas)
    
    for i, calle_base in enumerate(calles_ordenadas):
        if i % 50 == 0: 
            progreso.progress(i / total)
            texto_progreso.text(f"Analizando calle {i} de {total}...")
            
        if calle_base in procesados:
            continue
            
        # Esta calle será la "Oficial" de su grupo
        procesados.add(calle_base)
        mapa_correccion[calle_base] = calle_base
        
        # Buscamos parecidos en el resto de la lista
        # OPTIMIZACIÓN: Solo miramos las siguientes 500 para no tardar una eternidad
        # (Si la lista está ordenada alfabéticamente, los parecidos suelen estar cerca)
        rango_comparacion = calles_ordenadas[i+1 : i+500] 
        
        for calle_candidata in rango_comparacion:
            if calle_candidata in procesados:
                continue
            
            # Cálculo de similitud
            similitud = SequenceMatcher(None, calle_base, calle_candidata).ratio()
            
            if similitud >= umbral:
                # ¡Encontramos un parecido!
                mapa_correccion[calle_candidata] = calle_base
                procesados.add(calle_candidata)
    
    progreso.empty()
    texto_progreso.empty()
    return mapa_correccion

# --- INICIO APP ---
df = cargar_datos()

if df is not None:
    if 'CALLE' in df.columns:
        
        # 1. Normalización estricta (Reglas fijas)
        if 'CALLE_PRE' not in df.columns:
            with st.spinner("Expandiendo abreviaturas (SGTO, DR, RIO IV)..."):
                df['CALLE_PRE'] = df['CALLE'].astype(str).apply(expandir_abreviaturas)
        
        # 2. Fuzzy Matching (Agrupación por similitud)
        if 'CALLE_OFICIAL' not in df.columns:
            st.info("Buscando coincidencias del 70% para unificar variantes... (Esto puede tardar unos segundos)")
            
            # Obtenemos las únicas
            unicas = df['CALLE_PRE'].unique().tolist()
            
            # Generamos el diccionario de corrección
            diccionario_fuzzy = generar_mapa_fuzzy(unicas, umbral=0.70)
            
            # Aplicamos el diccionario
            df['CALLE_OFICIAL'] = df['CALLE_PRE'].map(diccionario_fuzzy)
            
            # Altura numérica
            df['ALTURA_NUM'] = pd.to_numeric(df['ALTURA'], errors='coerce').fillna(0).astype(int)

        # MÉTRICAS
        n_antes = df['CALLE'].nunique()
        n_final = df['CALLE_OFICIAL'].nunique()
        
        st.success(f"✅ Proceso Completo: De **{n_antes}** nombres originales bajamos a **{n_final}** calles unificadas.")
        
        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["🔎 BUSCADOR", "📋 VERIFICAR GRUPOS", "📥 DESCARGAR"])

        # TAB 1: BUSCADOR
        with tab1:
            col1, col2 = st.columns([2, 1])
            with col1:
                calles_ok = sorted(df['CALLE_OFICIAL'].unique())
                calle_sel = st.selectbox("Calle Unificada:", calles_ok)
            with col2:
                alt_sel = st.number_input("Altura:", step=100)
            
            if calle_sel:
                res = df[df['CALLE_OFICIAL'] == calle_sel]
                if alt_sel > 0:
                    res = res[
                        (res['ALTURA_NUM'] >= alt_sel - 200) & 
                        (res['ALTURA_NUM'] <= alt_sel + 200)
                    ]
                st.write(f"Vecinos: {len(res)}")
                
                # Mostrar columnas disponibles
                cols_view = ['APELLIDO', 'NOMBRE', 'DNI', 'CALLE_OFICIAL', 'ALTURA_NUM', 'CALLE']
                cols_view = [c for c in cols_view if c in df.columns]
                st.dataframe(res[cols_view])

        # TAB 2: AUDITORÍA (Ver qué unificó el Fuzzy)
        with tab2:
            st.write("Estos son los grupos que la IA unificó automáticamente:")
            # Agrupamos
            grupos = df.groupby('CALLE_OFICIAL')['CALLE'].unique().reset_index()
            grupos['Variantes'] = grupos['CALLE'].apply(len)
            grupos = grupos[grupos['Variantes'] > 1].sort_values('Variantes', ascending=False)
            st.dataframe(grupos)

        # TAB 3: DESCARGA
        with tab3:
            cols_exp = ['APELLIDO', 'NOMBRE', 'DNI', 'CALLE_OFICIAL', 'ALTURA_NUM', 'CALLE', 'ALTURA']
            cols_exp = [c for c in cols_exp if c in df.columns]
            
            csv = df[cols_exp].to_csv(index=False).encode('latin-1', errors='replace')
            st.download_button("📥 DESCARGAR BASE FINAL", csv, "padron_inteligente.csv", "text/csv", type="primary")

    else:
        st.error("No se encontró la columna 'CALLE'.")
