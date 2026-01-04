import streamlit as st
import pandas as pd
import re
from difflib import SequenceMatcher

# Configuración
st.set_page_config(page_title="Editor Maestro T3F", layout="wide", page_icon="🛠️")
st.title("🛠️ Padrón Inteligente con Edición Manual")

# --- 1. GESTIÓN DE ESTADO (Para guardar tus correcciones manuales) ---
if 'mapa_correcciones' not in st.session_state:
    st.session_state['mapa_correcciones'] = {}
if 'datos_cargados' not in st.session_state:
    st.session_state['datos_cargados'] = False

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

def generar_grupos_iniciales(lista_calles, umbral=0.70):
    calles_ordenadas = sorted(lista_calles)
    mapa = {} # {variante: oficial}
    procesados = set()
    
    # Barra de progreso
    bar = st.progress(0)
    for i, base in enumerate(calles_ordenadas):
        if i % 50 == 0: bar.progress(i / len(calles_ordenadas))
        
        if base in procesados: continue
        
        procesados.add(base)
        mapa[base] = base # El líder se apunta a sí mismo
        
        # Comparar con los siguientes 500
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

    # --- FASE 1: PRE-PROCESAMIENTO (Solo corre una vez) ---
    if not st.session_state['datos_cargados']:
        with st.spinner("Preparando datos y detectando grupos automáticos..."):
            # 1. Expandir
            df['CALLE_PRE'] = df['CALLE'].astype(str).apply(expandir_abreviaturas)
            unicas = df['CALLE_PRE'].unique().tolist()
            
            # 2. Agrupar (IA)
            # Guardamos el mapa en Session State para poder editarlo
            st.session_state['mapa_correcciones'] = generar_grupos_iniciales(unicas, umbral=0.70)
            st.session_state['datos_cargados'] = True
            st.rerun()

    # --- LOGICA DE MAPEO EN VIVO ---
    # Aplicamos el mapa actual (que puede tener tus correcciones manuales) al DF
    df['CALLE_OFICIAL'] = df['CALLE_PRE'].map(st.session_state['mapa_correcciones']).fillna(df['CALLE_PRE'])
    df['ALTURA_NUM'] = pd.to_numeric(df['ALTURA'], errors='coerce').fillna(0).astype(int)

    # --- INTERFAZ ---
    tab_editor, tab_audit, tab_final = st.tabs(["🛠️ EDITOR DE GRUPOS", "🔎 VERIFICAR", "📥 DESCARGAR"])

    # ---------------------------------------------------------
    # PESTAÑA 1: EL EDITOR MANUAL (LO QUE PEDISTE)
    # ---------------------------------------------------------
    with tab_editor:
        st.header("Control Humano de Grupos")
        st.markdown("Aquí puedes arreglar lo que la IA hizo mal. Si unió 'ALVEAR' con 'ITALIA', sepáralos aquí.")

        # 1. PREPARAR DATOS PARA EL SELECTOR
        # Invertimos el diccionario: {Oficial: [Lista de variantes]}
        grupos_dict = {}
        for variante, oficial in st.session_state['mapa_correcciones'].items():
            if oficial not in grupos_dict: grupos_dict[oficial] = []
            grupos_dict[oficial].append(variante)
        
        # Solo mostramos grupos que tienen variantes (o son interesantes)
        lista_grupos = sorted(grupos_dict.keys())
        
        # 2. SELECCIONAR GRUPO LÍDER
        col_sel, col_info = st.columns([2, 1])
        with col_sel:
            grupo_lider = st.selectbox("1. Elige el GRUPO PRINCIPAL a editar:", lista_grupos)
        
        if grupo_lider:
            miembros_actuales = grupos_dict.get(grupo_lider, [])
            
            with st.container(border=True):
                st.subheader(f"Editando grupo: {grupo_lider}")
                
                # --- A. ELIMINAR (SACAR INTRUSOS) ---
                st.write("**A. ¿Qué calles pertenecen a este grupo? (Desmarca las intrusas)**")
                st.caption("Ejemplo: Si ves 'ITALIA' aquí dentro, quítala presionando la X.")
                
                seleccionados = st.multiselect(
                    "Miembros del grupo:",
                    options=miembros_actuales,
                    default=miembros_actuales,
                    key="multiselect_miembros"
                )
                
                # Detectar qué borró el usuario
                borrados = set(miembros_actuales) - set(seleccionados)
                
                # --- B. AGREGAR (SUMAR OLVIDADOS) ---
                st.write("**B. ¿Falta alguna calle aquí? (Súmala)**")
                # Mostramos todas las calles posibles que NO están ya en este grupo
                todas_las_calles = sorted(list(st.session_state['mapa_correcciones'].keys()))
                candidatos = [c for c in todas_las_calles if c not in seleccionados]
                
                nuevos = st.multiselect("Buscar y agregar calles:", options=candidatos, placeholder="Escribe para buscar (Ej: ALVEAR)")
                
                # --- BOTÓN GUARDAR ---
                st.divider()
                if st.button("💾 CONFIRMAR CAMBIOS EN ESTE GRUPO", type="primary"):
                    # 1. Procesar los borrados: Se vuelven independientes
                    for b in borrados:
                        st.session_state['mapa_correcciones'][b] = b # Se apunta a sí misma
                        st.toast(f"Se sacó '{b}' del grupo.")
                    
                    # 2. Procesar los nuevos: Se apuntan al líder
                    for n in nuevos:
                        st.session_state['mapa_correcciones'][n] = grupo_lider
                        st.toast(f"Se agregó '{n}' al grupo.")
                    
                    st.success("¡Grupo actualizado! Recargando...")
                    st.rerun()

    # ---------------------------------------------------------
    # PESTAÑA 2: VERIFICAR RESULTADOS
    # ---------------------------------------------------------
    with tab_audit:
        st.subheader("Buscador de Resultados")
        col1, col2 = st.columns([2,1])
        with col1:
            # Lista actualizada con tus cambios
            finales = sorted(df['CALLE_OFICIAL'].unique())
            calle_ver = st.selectbox("Ver vecinos en:", finales)
        with col2:
            alt_ver = st.number_input("Altura:", step=100)
            
        if calle_ver:
            res = df[df['CALLE_OFICIAL'] == calle_ver]
            if alt_ver > 0:
                res = res[(res['ALTURA_NUM'] >= alt_ver - 200) & (res['ALTURA_NUM'] <= alt_ver + 200)]
            
            st.write(f"Total registros: {len(res)}")
            st.dataframe(res[['APELLIDO', 'NOMBRE', 'DNI', 'CALLE_OFICIAL', 'ALTURA_NUM', 'CALLE']])

    # ---------------------------------------------------------
    # PESTAÑA 3: DESCARGAR
    # ---------------------------------------------------------
    with tab_final:
        st.header("Descargar Trabajo Final")
        st.write("Este archivo ya tiene aplicadas todas tus correcciones manuales.")
        
        cols_exp = ['APELLIDO', 'NOMBRE', 'DNI', 'CALLE_OFICIAL', 'ALTURA_NUM', 'CALLE', 'ALTURA']
        cols_exp = [c for c in cols_exp if c in df.columns]
        
        csv = df[cols_exp].to_csv(index=False).encode('latin-1', errors='replace')
        st.download_button("📥 DESCARGAR CSV FINAL", csv, "padron_maestro.csv", "text/csv", type="primary")

else:
    st.error("Sube los datos procesados.")
