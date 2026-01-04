import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Editor Manual T3F", layout="wide", page_icon="✏️")
st.title("✏️ El Unificador Manual - Tres de Febrero")
st.markdown("Esta herramienta te permite seleccionar variantes de una calle y unificarlas bajo un solo nombre oficial.")

# --- 1. GESTIÓN DE ESTADO (MEMORIA TEMPORAL) ---
if 'correcciones' not in st.session_state:
    st.session_state['correcciones'] = {}

# --- 2. CARGA DE DATOS ---
@st.cache_data
def cargar_datos_crudos():
    try:
        df = pd.read_csv("datos.csv", encoding='latin-1', sep=None, engine='python')
        # Limpieza preliminar solo para sacar calles vacías
        df['CALLE_BRUTA'] = df['Domicilio'].apply(lambda x: re.search(r"^([A-Z\s\.\d\ñ\Ñ]+)", str(x).upper()).group(1).strip() if re.search(r"^([A-Z\s\.\d\ñ\Ñ]+)", str(x).upper()) else None)
        df = df.dropna(subset=['CALLE_BRUTA'])
        return df
    except Exception as e:
        return None

df = cargar_datos_crudos()

# --- 3. LOGICA DE CARGA DE TRABAJO PREVIO ---
uploaded_file = st.sidebar.file_uploader("📂 Cargar trabajo previo (correcciones.csv)", type=["csv"])
if uploaded_file is not None:
    try:
        df_prev = pd.read_csv(uploaded_file)
        # Cargamos al estado solo si es la primera vez
        if not st.session_state['correcciones']:
            st.session_state['correcciones'] = dict(zip(df_prev['Original'], df_prev['Corregido']))
            st.sidebar.success(f"Se cargaron {len(st.session_state['correcciones'])} reglas previas.")
    except:
        st.sidebar.error("Error cargando archivo previo.")

# --- INTERFAZ PRINCIPAL ---

if df is not None:
    # Filtramos las calles que YA tienen corrección para no mostrarlas
    calles_totales = sorted(df['CALLE_BRUTA'].unique())
    
    # Métrica de progreso
    total_variantes = len(calles_totales)
    corregidas = len([c for c in calles_totales if c in st.session_state['correcciones']])
    
    st.progress(corregidas / total_variantes)
    st.caption(f"Progreso: {corregidas} variantes corregidas de {total_variantes} nombres únicos encontrados.")

    col1, col2 = st.columns([1, 2])

    # --- PANEL IZQUIERDO: BUSCADOR Y SELECCIÓN ---
    with col1:
        st.subheader("1. Buscar y Agrupar")
        
        # A. Buscador
        busqueda = st.text_input("Escribe parte del nombre (Ej: CAFER)", key="search_box").upper()
        
        # B. Filtrar opciones
        if busqueda:
            opciones_visibles = [c for c in calles_totales if busqueda in c]
        else:
            opciones_visibles = []
            st.info("Escribe algo arriba para buscar variantes.")

        # C. Selector Multiusuario
        # Pre-marcamos las que coinciden con la búsqueda pero dejamos desmarcar
        seleccionadas = st.multiselect(
            "Selecciona todas las variantes que sean la misma calle:",
            options=opciones_visibles,
            default=opciones_visibles # Por defecto selecciona todo lo que encontraste
        )

        # D. Input del Nombre Correcto
        if seleccionadas:
            # Sugerimos el nombre más largo o el primero como default
            default_name = max(seleccionadas, key=len) 
            nombre_oficial = st.text_input("¿Cómo se debe llamar esta calle?", value=default_name).upper().strip()
            
            if st.button("✅ UNIFICAR ESTAS CALLES", type="primary"):
                # Guardamos en la memoria
                for variante in seleccionadas:
                    st.session_state['correcciones'][variante] = nombre_oficial
                
                st.success(f"¡Listo! {len(seleccionadas)} variantes ahora son '{nombre_oficial}'.")
                st.rerun() # Recargamos para limpiar

    # --- PANEL DERECHO: VISOR DE REGLAS Y DESCARGA ---
    with col2:
        st.subheader("2. Reglas Creadas")
        
        if st.session_state['correcciones']:
            # Convertimos dict a DataFrame para mostrar
            df_reglas = pd.DataFrame(list(st.session_state['correcciones'].items()), columns=['Original', 'Corregido'])
            
            # Mostramos tabla
            st.dataframe(df_reglas.sort_values('Corregido'), height=400, use_container_width=True)
            
            # --- BOTÓN DE DESCARGA (LO MÁS IMPORTANTE) ---
            st.divider()
            csv = df_reglas.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 DESCARGAR ARCHIVO FINAL (correcciones.csv)",
                data=csv,
                file_name="correcciones.csv",
                mime="text/csv",
                type="primary"
            )
            st.warning("⚠️ Importante: Cada vez que termines una sesión, DESCARGA este archivo. La próxima vez, súbelo en el menú de la izquierda para continuar donde dejaste.")
        else:
            st.info("Aún no has creado ninguna regla. Busca una calle a la izquierda y unifícala.")

else:
    st.error("No se encuentra 'datos.csv'. Súbelo a GitHub.")
