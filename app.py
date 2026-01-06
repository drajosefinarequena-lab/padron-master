import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(page_title="Editor de Padrón", layout="wide")

st.title("Procesador y Editor de Padrón")
st.markdown("""
**Instrucciones:**
1. Sube tu archivo (puede ser el `datos.csv` original o uno ya procesado).
2. Si es el original, el sistema separará las calles.
3. **Edita manualmente** en la tabla.
4. Descarga el resultado final.
""")

# ---------------------------------------------------------
# 1. CARGA DE ARCHIVO
# ---------------------------------------------------------
uploaded_file = st.file_uploader("Elige tu archivo CSV", type=['csv'])

# ---------------------------------------------------------
# 2. FUNCIONES
# ---------------------------------------------------------
localities_to_remove = [
    'CASEROS', 'CIUDADELA', 'PABLO PODESTA', 'LOMA HERMOSA', 'VILLA BOSCH', 
    'MARTIN CORONADO', 'SANTOS LUGARES', 'SAENZ PEÑA', 'EL LIBERTADOR', 
    'CIUDAD JARDIN LOMAS DEL PALOMAR', 'JOSE INGENIEROS', 'REMEDIOS DE ESCALADA', 
    '11 DE SEPTIEMBRE', 'CHURRUCA', 'VILLA RAFFO', 'NO CONSTA'
]

def limpiar_domicilio(domicilio_str):
    if not isinstance(domicilio_str, str):
        return pd.Series([None, None, None, None, None])
    
    parts = [p.strip() for p in domicilio_str.split(',')]
    if parts and parts[-1] == 'TRES DE FEBRERO': parts.pop()
    if parts and parts[-1] in localities_to_remove: parts.pop()
        
    cp, piso, depto = None, None, None
    remaining = []
    
    for p in parts:
        p_upper = p.upper()
        if p_upper.startswith('CP:') or p_upper.startswith('C.P.') or p_upper.startswith('CP '):
            cp = re.sub(r'^(CP:|C\.P\.|CP)\s*', '', p_upper).strip()
        elif 'PISO' in p_upper or p_upper.startswith('PISO:'):
             piso = re.sub(r'PISO:?\s*', '', p_upper).strip()
        elif 'DEPTO' in p_upper or 'DPTO' in p_upper:
             depto = re.sub(r'(DEPTO|DPTO):?\s*', '', p_upper).strip()
        else:
            remaining.append(p)
            
    street_full = ", ".join(remaining).strip()
    calle, altura = None, None
    
    if street_full:
        s = street_full
        if s.endswith('S/N'): s = s[:-3].strip()
        match = re.search(r'^(.*)\s+(\d+(?:[a-zA-Z])?)$', s)
        if match:
            calle = match.group(1).strip()
            altura = match.group(2).strip()
        else:
            if s == 'S/N' or s == '': calle, altura = None, 'S/N'
            else: calle, altura = s, None
                 
    if calle:
        calle = calle.upper()
        calle = calle.replace('NO CONSTA', '')
        calle = re.sub(r'\bS/N\b', '', calle)
        replacements = [
            (r'\bAV\.', 'AVENIDA'), (r'\bAV\b', 'AVENIDA'),
            (r'\bGRAL\.', 'GENERAL'), (r'\bGRAL\b', 'GENERAL'),
            (r'\bTTE\.', 'TENIENTE'), (r'\bDR\.', 'DOCTOR'),
            (r'\bPJE\.', 'PASAJE'), (r'\b3 DE FEB\b', '3 DE FEBRERO'),
            (r'\bJ\.\s*F\.\s*KENNEDY\b', 'JOHN F. KENNEDY'),
        ]
        for pat, repl in replacements: calle = re.sub(pat, repl, calle)
        calle = re.sub(r'CP[:\s]\s*\d+', '', calle)
        calle = re.sub(r'\s+', ' ', calle).strip()
        if re.match(r'^\d+$', calle) and not altura:
            altura, calle = calle, None
    
    return pd.Series([calle, altura, piso, depto, cp])

@st.cache_data
def cargar_y_procesar(file):
    # Intentar leer normal (con encabezados)
    file.seek(0)
    df = pd.read_csv(file)
    
    # CASO 1: Archivo Original (tiene columna Domicilio)
    if 'Domicilio' in df.columns:
        nuevas = df['Domicilio'].apply(limpiar_domicilio)
        nuevas.columns = ['Calle', 'Altura', 'Piso', 'Depto', 'Codigo_Postal']
        df_final = pd.concat([df, nuevas], axis=1)
        df_final.drop(columns=['Domicilio'], inplace=True)
        return df_final, "Procesado desde original"

    # CASO 2: Archivo ya procesado (tiene Calle/Altura)
    elif 'Calle' in df.columns and 'Altura' in df.columns:
        return df, "Archivo ya procesado detectado"

    # CASO 3: Archivo sin encabezados (detectado por falta de columnas clave)
    else:
        # Probamos leer sin header
        file.seek(0)
        df_sin_header = pd.read_csv(file, header=None)
        cols = len(df_sin_header.columns)
        
        # Asignamos nombres según la cantidad de columnas (estructura típica de tu archivo)
        if cols == 8:
            df_sin_header.columns = ['Apellido', 'Nombre', 'Matricula', 'F_Nacimiento', 'Calle', 'Altura', 'Piso', 'Depto']
            return df_sin_header, "Archivo sin cabecera detectado (8 columnas)"
        elif cols >= 5:
            # Intento genérico si no coincide exacto
            st.warning(f"El archivo tiene {cols} columnas y no tiene cabecera clara. Se intentará editar así.")
            return df_sin_header, "Archivo sin cabecera genérico"
        
        return None, "Error: No se reconoce el formato del archivo (falta columna Domicilio o Calle)."

# ---------------------------------------------------------
# 3. LÓGICA PRINCIPAL
# ---------------------------------------------------------
if uploaded_file is not None:
    df_procesado, msg = cargar_y_procesar(uploaded_file)
    
    if df_procesado is not None:
        st.success(f"Archivo cargado correctamente: {msg}")
        
        st.subheader("Editor de Datos")
        st.info("💡 Haz doble clic en las celdas para corregir errores.")
        
        # EDITOR INTERACTIVO
        df_editado = st.data_editor(df_procesado, num_rows="dynamic", use_container_width=True, height=600)
        
        st.write("---")
        
        # DESCARGA
        csv_buffer = df_editado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV Final",
            data=csv_buffer,
            file_name="padron_final_editado.csv",
            mime="text/csv",
        )
    else:
        st.error(msg)
else:
    st.info("Esperando archivo...")
