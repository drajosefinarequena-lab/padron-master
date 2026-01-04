import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(page_title="Padrón T3F - Final", layout="wide", page_icon="📍")
st.title("📍 Padrón Unificado y Limpio - Tres de Febrero")

# --- 1. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    archivo = "datos_procesados - datos_procesados.csv"
    try:
        # Leemos sin encabezado porque vimos que no tiene
        df = pd.read_csv(archivo, header=None, encoding='latin-1')
        
        # Renombramos las columnas clave según lo que investigamos
        # 0:Apellido, 1:Nombre, 2:DNI, 4:CALLE, 5:ALTURA
        df = df.rename(columns={
            0: 'Apellido',
            1: 'Nombre',
            2: 'DNI',
            4: 'Calle_Cruda',
            5: 'Altura_Cruda'
        })
        
        # Convertimos altura a número (manejando errores)
        df['Altura_Num'] = pd.to_numeric(df['Altura_Cruda'], errors='coerce').fillna(0).astype(int)
        
        return df
    except FileNotFoundError:
        st.error(f"No encuentro el archivo: {archivo}")
        return None

# --- 2. LA APLANADORA (Tu lógica de limpieza acumulada) ---
def unificar_a_la_fuerza(texto):
    if not isinstance(texto, str): return ""
    
    # 1. Normalización básica
    calle = texto.upper().strip()
    calle = calle.replace(".", " ") # C. GARDEL -> C  GARDEL
    calle = " ".join(calle.split()) # Quitar espacios dobles
    
    # 2. REGLAS DE ORO (Las que definimos juntos)
    
    # MITRE (El caso más difícil)
    if "MITRE" in calle: return "BARTOLOME MITRE"
    
    # GARDEL
    if "GARDEL" in calle: return "CARLOS GARDEL"
    
    # ANCHORDOQUI (Todas las variantes vascas)
    if "ANCHORDO" in calle: return "DR ENRIQUE ANCHORDOQUI"
    
    # CAFFERATA (Arreglando las F y T)
    if "CAFER" in calle or "CAFFER" in calle: return "CAFFERATA"
    
    # SAN MARTÍN (Distinguiendo Av de Boulevard)
    if "SAN MARTIN" in calle:
        if any(x in calle for x in ["BV", "BOULEVARD", "B AL", "RIO"]):
            return "BOULEVARD SAN MARTIN"
        return "AV SAN MARTIN"
        
    # MILITAR
    if "MILITAR" in calle: return "AV MILITAR"
    
    # ALVEAR
    if "ALVEAR" in calle: return "MARCELO T DE ALVEAR"
    
    # URQUIZA
    if "URQUIZA" in calle: return "URQUIZA"
    
    # ROSAS
    if "ROSAS" in calle and any(x in calle for x in ["JUAN", "MANUEL", "BRIG"]): 
        return "JUAN MANUEL DE ROSAS"
    
    # YRIGOYEN
    if "YRIGOYEN" in calle or "IRIGOYEN" in calle: return "HIPOLITO YRIGOYEN"
    
    # PELLEGRINI
    if "PELLEGRINI" in calle or "PELEGRINI" in calle: return "CARLOS PELLEGRINI"
    
    # PAZ
    if "PAZ" in calle and ("GRAL" in calle or "GENERAL" in calle): return "AV GENERAL PAZ"
    
    # CERRO AMARILLO (El problema de la C)
    if "AMARILLO" in calle and ("CERRO" in calle or "C " in calle or calle.startswith("C ")): 
        return "CERRO AMARILLO"
    
    # GLADIOLOS
    if "GLADIOLO" in calle: return "DE LOS GLADIOLOS"

    # 3. LIMPIEZA GENÉRICA (Si no cayó en ninguna regla especial)
    # Quitamos prefijos comunes
    basura = ["AV ", "AV.", "AVENIDA ", "CALLE ", "DR ", "DR.", "GRAL ", "GRAL.", "PJE ", "PJE."]
    calle_limpia = calle
    for b in basura:
        if calle_limpia.startswith(b):
            calle_limpia = calle_limpia.replace(b, "")
            
    return calle_limpia.strip()

# --- INICIO DE LA APP ---
df = cargar_datos()

if df is not None:
    # Aplicamos la limpieza en vivo
    if 'Calle_Oficial' not in df.columns:
        with st.spinner('Aplicando reglas de limpieza a las calles...'):
            df['Calle_Oficial'] = df['Calle_Cruda'].apply(unificar_a_la_fuerza)
            
            # Limpieza extra: Eliminamos registros sin calle válida
            df = df[df['Calle_Oficial'] != ""]

    # --- INTERFAZ ---
    tab1, tab2 = st.tabs(["🏠 BUSCADOR POR CALLE", "👤 BUSCADOR POR PERSONA"])
    
    # MODO CALLE
    with tab1:
        # Selector de calles ya limpias
        lista_calles = sorted(df['Calle_Oficial'].unique())
        calle_sel = st.selectbox("Selecciona Calle:", lista_calles)
        
        col1, col2 = st.columns([1, 1])
        altura_sel = col1.number_input("Altura (Opcional):", value=0, step=100)
        rango = col2.slider("Radio de búsqueda (metros):", 100, 500, 200)
        
        if calle_sel:
            # Filtramos
            resultados = df[df['Calle_Oficial'] == calle_sel]
            
            # Si puso altura, filtramos por rango
            if altura_sel > 0:
                resultados = resultados[
                    (resultados['Altura_Num'] >= altura_sel - rango) &
                    (resultados['Altura_Num'] <= altura_sel + rango)
                ]
                # Ordenamos por cercanía
                resultados['Distancia'] = abs(resultados['Altura_Num'] - altura_sel)
                resultados = resultados.sort_values('Distancia')
            else:
                # Ordenamos por numeración
                resultados = resultados.sort_values('Altura_Num')
            
            st.success(f"Encontrados: {len(resultados)} vecinos.")
            st.dataframe(
                resultados[['Apellido', 'Nombre', 'Calle_Oficial', 'Altura_Num', 'Calle_Cruda']], 
                use_container_width=True
            )

    # MODO PERSONA
    with tab2:
        busqueda = st.text_input("Apellido o DNI:")
        if busqueda:
            filtro = df[
                df['Apellido'].astype(str).str.contains(busqueda.upper(), na=False) |
                df['DNI'].astype(str).str.contains(busqueda, na=False)
            ]
            st.dataframe(filtro[['Apellido', 'Nombre', 'DNI', 'Calle_Oficial', 'Altura_Num']])

else:
    st.info("Esperando carga de datos...")
