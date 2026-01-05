import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher

# Configuración
st.set_page_config(page_title="Editor Maestro T3F", layout="wide", page_icon="🛠️")
st.title("🛠️ Padrón Inteligente: Flujo de Trabajo")

# --- 1. GESTIÓN DE ESTADO ---
if 'mapa_correcciones' not in st.session_state:
    st.session_state['mapa_correcciones'] = {}
if 'datos_cargados' not in st.session_state:
    st.session_state['datos_cargados'] = False

# NUEVO: Estado para recordar qué grupos ya revisaste y ocultarlos
if 'revisados' not in st.session_state:
    st.session_state['revisados'] = set()

# --- 2. CARGA DE DATOS ---
@st.cache_data
def cargar_datos_iniciales():
    archivo = "datos_procesados - datos_procesados (1).csv"
    try:
        try:
            df = pd.read_csv(archivo, encoding='latin-1')
        except:
            df = pd.read_csv(archivo, encoding='utf-8')
        
        df.columns = [c.upper().strip() for c in df.columns]
        return df
    except FileNotFoundError:
        return None

# --- 3. FUNCIONES DE LIMPIEZA ---
def expandir_abreviaturas(texto):
    if not isinstance(texto, str): return ""
    calle = texto.upper().strip()
    calle = re.sub(r"[.]", " ", calle)
    calle = re.sub(r"\s+", " ", calle)
    
    reemplazos = {
        r"\bSGTO\b": "SARGENTO", r"\bDR\b": "DOCTOR", r"\bDOC\b": "DOCTOR",
        r"\bDRA\b": "DOCTORA", r"\bGRAL\b": "GENERAL", r"\bCNEL\b": "CORONEL",
        r"\bTTE\b": "TENIENTE", r"\bSUBTTE\b": "SUBTENIENTE", r"\bALMTE\b": "ALMIRANTE",
        r"\bCDTE\b": "COMANDANTE", r"\bPROF\b": "PROFESOR", r"\bING\b": "INGENIERO",
        r"\bARQ\b": "ARQUITECTO", r"\bPBR\b": "PRESBITERO", r"\bPCIA\b": "PROVINCIA",
        r"\bLIB\b": "LIBERTADOR", r"\bAV\b": "AVENIDA", r"\bAVDA\b": "AVENIDA",
        r"\bBV\b": "BOULEVARD", r"\bPJE\b": "PASAJE",
    }
    for patron, reemplazo in reemplazos.items():
        calle = re.sub(patron, reemplazo, calle)

    calle = re.sub(r"\bR\s+(JACHAL|CUARTO|NEGRO|SALADO|DIAMANTE|TERCERO)\b", r"RIO \1", calle)
    calle = re.sub(r"\bRIO\s+(4|IV)\b", "RIO CUARTO", calle)
    calle = re.sub(r"\bRIO\s+(3|III)\b", "RIO TERCERO", calle)
    calle = re.sub(r"\b(1RO|1|I)\s+DE\s+MAYO\b", "1 DE MAYO", calle)
    calle = re.sub(r"\b(3|III)\s+DE\s+FEBRERO\b", "3 DE FEBRERO", calle)
    calle = re.sub(r"\b(STA|S)\s+RITA\b", "SANTA RITA", calle)
    calle = re.sub(r"\b(STO|S)\s+IGNACIO\b", "SAN IGNACIO", calle)
    calle = re.sub(r"\b(STA|S)\s+MARIA\b", "SANTA MARIA", calle)
    calle = re.sub(r"\b(STO|S)\s+MARTIN\b", "SAN MARTIN", calle)
    
    return calle.strip()

@st.cache_data
def crear_columna_preprocesada(df):
    return df['CALLE'].astype(str).apply(expandir_abreviaturas)

def generar_grupos_iniciales(lista_calles, umbral=0.70):
    calles_ordenadas = sorted(lista_calles)
    mapa = {} 
    procesados = set()
    
    bar = st.progress(0)
    total = len(calles_ordenadas)
    
    for i, base in enumerate(calles_ordenadas):
        if i % 50 == 0: bar.progress(i / total)
        
        if base in procesados: continue
        
        procesados.add(base)
        mapa[base] = base 
        
        rango = calles_ordenadas[i+1 : i+500]
        for candidata in rango:
            if candidata in procesados: continue
            
            if SequenceMatcher(None, base, candidata).ratio() >= umbral:
                mapa[candidata] = base
                procesados.add(candidata)
    bar.empty()
    return mapa

# --- INICIO APP ---
df = cargar_datos_iniciales()

if df is not None:
    if 'CALLE' not in df.columns:
        st.error("Falta columna 'CALLE'")
        st.stop()

    df['CALLE_PRE'] = crear_columna_preprocesada(df)

    # --- FASE 1: DETECCIÓN (Solo primera vez) ---
    if not st.session_state['datos_cargados']:
        with st.spinner("Inicializando motor de inteligencia..."):
            unicas = df['CALLE_PRE'].unique().tolist()
            st.session_state['mapa_correcciones'] = generar_grupos_iniciales(unicas, umbral=0.70)
            st.session_state['datos_cargados'] = True
            st.rerun()

    # --- APLICAR MAPA EN VIVO ---
    df['CALLE_OFICIAL'] = df['CALLE_PRE'].map(st.session_state['mapa_correcciones']).fillna(df['CALLE_PRE'])
    df['ALTURA_NUM'] = pd.to_numeric(df['ALTURA'], errors='coerce').fillna(0).astype(int)

    # --- INTERFAZ ---
    tab_editor, tab_audit, tab_final = st.tabs(["📝 LISTA DE TAREAS (EDITOR)", "🔎 VERIFICAR", "📥 DESCARGAR"])

    # ---------------------------------------------------------
    # PESTAÑA 1: EDITOR (TAREAS PENDIENTES)
    # ---------------------------------------------------------
    with tab_editor:
        st.header("Control de Calidad: Calle por Calle")
        
        # 1. Preparar listas
        grupos_dict = {}
        for variante, oficial in st.session_state['mapa_correcciones'].items():
            if oficial not in grupos_dict: grupos_dict[oficial] = []
            grupos_dict[oficial].append(variante)
        
        total_grupos = len(grupos_dict)
        # Filtramos los que NO están en revisados
        pendientes = [g for g in sorted(grupos_dict.keys()) if g not in st.session_state['revisados']]
        
        # BARRA DE PROGRESO
        hechos = total_grupos - len(pendientes)
        if total_grupos > 0:
            progreso = hechos / total_grupos
            st.progress(progreso, text=f"Progreso: {hechos} revisados de {total_grupos} totales.")
        
        col_reset, col_vacio = st.columns([1, 4])
        if col_reset.button("🔄 Mostrar ocultos"):
            st.session_state['revisados'] = set()
            st.rerun()

        st.divider()

        # 2. SELECTOR (Solo muestra pendientes)
        if pendientes:
            st.success(f"Te quedan **{len(pendientes)}** calles por revisar.")
            
            col_sel, col_info = st.columns([2, 1])
            with col_sel:
                grupo_lider = st.selectbox("👉 Selecciona siguiente calle:", pendientes)
            
            if grupo_lider:
                miembros_actuales = grupos_dict.get(grupo_lider, [])
                
                with st.container(border=True):
                    st.subheader(f"Editando: {grupo_lider}")
                    
                    # A. ELIMINAR
                    st.write("**A. Variantes actuales (Desmarca las incorrectas):**")
                    seleccionados = st.multiselect(
                        "Calles agrupadas:",
                        options=miembros_actuales,
                        default=miembros_actuales,
                        key="multi_miembros"
                    )
                    borrados = set(miembros_actuales) - set(seleccionados)
                    
                    # B. AGREGAR
                    st.write("**B. Buscar calles perdidas para sumar:**")
                    todas = sorted(list(st.session_state['mapa_correcciones'].keys()))
                    candidatos = [c for c in todas if c not in seleccionados]
                    nuevos = st.multiselect("Agregar manual:", options=candidatos, placeholder="Escribe para buscar...")
                    
                    st.divider()
                    
                    # BOTÓN DE ACCIÓN
                    # "Confirmar y Ocultar"
                    if st.button("✅ CONFIRMAR Y FINALIZAR ESTA CALLE", type="primary"):
                        # 1. Aplicar cambios lógicos
                        for b in borrados:
                            st.session_state['mapa_correcciones'][b] = b 
                        for n in nuevos:
                            st.session_state['mapa_correcciones'][n] = grupo_lider
                        
                        # 2. MARCAR COMO REVISADO (MAGIA)
                        st.session_state['revisados'].add(grupo_lider)
                        
                        st.toast(f"Calle '{grupo_lider}' procesada y archivada.")
                        st.rerun() # Al recargar, desaparece de la lista 'pendientes'
        else:
            st.balloons()
            st.success("¡Felicidades! Has revisado todas las calles.")

    # ---------------------------------------------------------
    # PESTAÑA 2: VERIFICAR
    # ---------------------------------------------------------
    with tab_audit:
        st.subheader("Verificar cómo queda el padrón")
        col1, col2 = st.columns([2,1])
        with col1:
            finales = sorted(df['CALLE_OFICIAL'].unique())
            calle_ver = st.selectbox("Ver vecinos en:", finales)
        with col2:
            alt_ver = st.number_input("Altura:", step=100)
            
        if calle_ver:
            res = df[df['CALLE_OFICIAL'] == calle_ver]
            if alt_ver > 0:
                res = res[(res['ALTURA_NUM'] >= alt_ver - 200) & (res['ALTURA_NUM'] <= alt_ver + 200)]
            
            st.write(f"Registros: {len(res)}")
            cols_ver = ['APELLIDO', 'NOMBRE', 'DNI', 'CALLE_OFICIAL', 'ALTURA_NUM', 'CALLE']
            cols_ver = [c for c in cols_ver if c in df.columns]
            st.dataframe(res[cols_ver])

    # ---------------------------------------------------------
    # PESTAÑA 3: DESCARGAR
    # ---------------------------------------------------------
    with tab_final:
        st.header("Descarga Final")
        st.write("Solo descarga cuando hayas terminado de revisar todo.")
        
        cols_exp = ['APELLIDO', 'NOMBRE', 'DNI', 'CALLE_OFICIAL', 'ALTURA_NUM', 'CALLE', 'ALTURA']
        cols_exp = [c for c in cols_exp if c in df.columns]
        
        csv = df[cols_exp].to_csv(index=False).encode('latin-1', errors='replace')
        st.download_button("📥 DESCARGAR PADRÓN MAESTRO", csv, "padron_maestro.csv", "text/csv", type="primary")

else:
    st.error("Falta el archivo en GitHub.")
