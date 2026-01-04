import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Editor Manual T3F", layout="wide", page_icon="✂️")
st.title("✂️ Editor de Calles (Separa Alturas)")
st.markdown("""
**Instrucciones:**
1. Esta herramienta corta los números temporalmente para que veas solo los nombres de calle.
2. Agrupa las variantes (ej: CAFERATA, CAFERETA) y dales un nombre oficial.
3. Al final, descarga el archivo `correcciones.csv`.
**Nota:** La altura de cada vecino se conserva intacta en la base de datos original.
""")

# --- 1. GESTIÓN DE MEMORIA ---
if 'correcciones' not in st.session_state:
    st.session_state['correcciones'] = {}

# --- 2. FUNCIÓN DE CORTE (LA TIJERA) ---
def separar_calle_altura(texto):
    if not isinstance(texto, str): return texto, 0
    t = texto.upper().strip()
    # Regex: Busca texto al principio y números al final
    match = re.search(r"^(.+?)\s+(\d+)$", t)
    if match:
        calle = match.group(1).strip()
        return calle
    return t # Si no tiene número, devuelve todo el texto

# --- 3. CARGA DE DATOS ---
@st.cache_data
def cargar_y_cortar():
    try:
        df = pd.read_csv("datos.csv", encoding='latin-1', sep=None, engine='python')
        
        # Detectamos columna domicilio
        col_dom = 'Domicilio' if 'Domicilio' in df.columns else df.columns[0]
        
        # APLICAMOS LA TIJERA: Creamos una columna solo con nombres
        df['NOMBRE_SOLO'] = df[col_dom].apply(separar_calle_altura)
        
        # Eliminamos vacíos y ordenamos
        nombres_unicos = sorted(df['NOMBRE_SOLO'].dropna().unique())
        return nombres_unicos
    except:
        return []

nombres_unicos = cargar_y_cortar()

# --- 4. CARGAR TRABAJO PREVIO ---
with st.sidebar:
    st.header("📂 Cargar/Guardar")
    uploaded = st.file_uploader("Subir correcciones.csv existente", type=["csv"])
    if uploaded:
        try:
            df_prev = pd.read_csv(uploaded)
            # Cargamos al diccionario
            nuevas_reglas = dict(zip(df_prev['Original'], df_prev['Corregido']))
            st.session_state['correcciones'].update(nuevas_reglas)
            st.success(f"Cargadas {len(nuevas_reglas)} reglas.")
        except:
            st.error("Error leyendo archivo.")

# --- INTERFAZ ---
if nombres_unicos:
    # Calculamos pendientes (los que no están en el diccionario de correcciones)
    pendientes = [c for c in nombres_unicos if c not in st.session_state['correcciones']]
    
    col1, col2 = st.columns([1, 2])
    
    # --- PANEL IZQUIERDO: TRABAJO ---
    with col1:
        st.subheader("🛠️ Zona de Trabajo")
        st.write(f"Nombres únicos encontrados: **{len(nombres_unicos)}**")
        st.write(f"Pendientes de revisar: **{len(pendientes)}**")
        
        # Buscador
        busqueda = st.text_input("🔍 Buscar calle (Ej: CAFER):", key="search").upper()
        
        if busqueda:
            # Filtramos opciones que coincidan con la búsqueda
            opciones = [c for c in nombres_unicos if busqueda in c]
            
            if opciones:
                st.write("Selecciona las variantes a unificar:")
                seleccionadas = st.multiselect(
                    "Variantes encontradas:",
                    options=opciones,
                    default=opciones # Se auto-seleccionan para agilizar
                )
                
                if seleccionadas:
                    # Elegimos el nombre más largo como sugerencia
                    sugerencia = max(seleccionadas, key=len)
                    
                    nombre_oficial = st.text_input("📝 Nombre Oficial Correcto:", value=sugerencia).upper()
                    
                    if st.button("✅ GUARDAR UNIFICACIÓN", type="primary"):
                        # Guardamos en memoria
                        for sucio in seleccionadas:
                            st.session_state['correcciones'][sucio] = nombre_oficial
                        st.success("¡Guardado!")
                        st.rerun()
            else:
                st.warning("No se encontraron calles con ese nombre.")
        else:
            st.info("Escribe arriba para empezar a limpiar.")

    # --- PANEL DERECHO: RESULTADOS ---
    with col2:
        st.subheader("📋 Reglas Generadas")
        
        if st.session_state['correcciones']:
            # Convertimos a DataFrame
            df_reglas = pd.DataFrame(list(st.session_state['correcciones'].items()), columns=['Original', 'Corregido'])
            
            # Mostramos la tabla
            st.dataframe(df_reglas.sort_values('Corregido'), use_container_width=True, height=500)
            
            # BOTÓN DE DESCARGA
            csv_data = df_reglas.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ DESCARGAR correcciones.csv (Fundamental)",
                data=csv_data,
                file_name="correcciones.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.write("Aquí aparecerá la lista de tus correcciones.")

else:
    st.error("No se pudo leer 'datos.csv'. Súbelo a GitHub.")
