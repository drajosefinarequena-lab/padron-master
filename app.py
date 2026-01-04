import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Separador de Direcciones", layout="wide", page_icon="🏗️")
st.title("🏗️ Separador de Direcciones")
st.markdown("""
Esta herramienta toma tu columna de dirección mezclada y la separa en:
**CALLE | ALTURA | RESTO (Piso, Depto, etc.)**
""")

# --- 1. FUNCIÓN DE SEPARACIÓN (LA CIRUGÍA) ---
def separar_direccion(texto):
    if not isinstance(texto, str):
        return pd.Series([None, None, None])
    
    texto = texto.upper().strip()
    
    # LÓGICA: Buscamos el ÚLTIMO número de la cadena que esté separado por espacio
    # Ejemplo: "CAFFERATA 5472 CASEROS" -> Calle: CAFFERATA, Altura: 5472, Resto: CASEROS
    # Regex: 
    # ^(.+?)    -> (Grupo 1) Todo el texto del principio (Calle)
    # \s+       -> Un espacio
    # (\d+)     -> (Grupo 2) El número (Altura)
    # \s*(.*)$  -> (Grupo 3) Lo que sobre al final (Localidad, piso, etc)
    
    match = re.search(r"^(.+?)\s+(\d+)\s*(.*)$", texto)
    
    if match:
        calle = match.group(1).strip()
        altura = match.group(2).strip()
        resto = match.group(3).strip()
        return pd.Series([calle, altura, resto])
    else:
        # Si no encontramos número, devolvemos todo en calle y lo demás vacío
        return pd.Series([texto, None, None])

# --- 2. CARGA Y PROCESAMIENTO ---
uploaded_file = st.file_uploader("Sube tu archivo sucio (CSV o Excel)", type=["csv", "xlsx"])

if uploaded_file:
    # Cargar archivo
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='latin-1', sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success(f"Archivo cargado: {len(df)} filas.")
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        st.stop()

    # Detectar columna domicilio
    cols = df.columns.tolist()
    # Buscamos si existe 'Domicilio' o 'Direccion', sino usamos la primera
    col_dom = next((c for c in cols if 'DOMICILIO' in c.upper() or 'DIRECCION' in c.upper()), cols[0])
    
    st.write(f"Separando datos de la columna: **{col_dom}**")

    if st.button("🚀 SEPARAR EN COLUMNAS", type="primary"):
        with st.spinner("Realizando cirugía a las direcciones..."):
            
            # APLICAMOS LA FUNCIÓN
            nuevas_cols = df[col_dom].apply(separar_direccion)
            nuevas_cols.columns = ['CALLE_LIMPIA', 'ALTURA', 'DETALLES_EXTRA']
            
            # UNIMOS AL DATAFRAME ORIGINAL
            df_final = pd.concat([df, nuevas_cols], axis=1)
            
            # Agregamos columnas vacías que pediste para completar en Excel
            if 'LOCALIDAD' not in df_final.columns:
                df_final['LOCALIDAD'] = "Tres de Febrero" # Valor por defecto
            if 'PARTIDO' not in df_final.columns:
                df_final['PARTIDO'] = "Tres de Febrero"
            if 'CP' not in df_final.columns:
                df_final['CP'] = ""

            # REORDENAMOS PARA QUE SEA CÓMODO EDITAR
            # Ponemos las columnas nuevas al principio junto con Nombre/Apellido
            cols_prioridad = ['Apellido', 'Nombre', 'CALLE_LIMPIA', 'ALTURA', 'DETALLES_EXTRA', 'LOCALIDAD', 'CP']
            cols_existentes = [c for c in cols_prioridad if c in df_final.columns]
            cols_resto = [c for c in df_final.columns if c not in cols_existentes]
            
            df_export = df_final[cols_existentes + cols_resto]

            st.balloons()
            st.subheader("Vista Previa del Resultado:")
            st.dataframe(df_export.head())

            # BOTÓN DESCARGA
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 DESCARGAR ARCHIVO ESTRUCTURADO (Excel)",
                data=csv,
                file_name="base_estructurada.csv",
                mime="text/csv"
            )
            
            st.success("""
            **¡PASOS SIGUIENTES!**
            1. Descarga este archivo.
            2. Ábrelo en Excel.
            3. Ordena por la columna **'CALLE_LIMPIA'**.
            4. ¡Ahora verás todos los 'CAFFERATA' juntos! Corrige los nombres masivamente arrastrando celdas.
            5. Cuando termines, guarda ese archivo y será tu nueva **Base Maestra**.
            """)

else:
    st.info("Sube un archivo para comenzar.")
