import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(page_title="Limpieza y Edición de Padrón", layout="wide")

st.title("Procesador y Editor de Padrón")
st.markdown("1. Sube tu archivo `datos.csv`.\n2. El sistema separará calles y alturas automáticamente.\n3. **Edita manualmente** cualquier error en la tabla de abajo.\n4. Descarga el archivo final.")

# ---------------------------------------------------------
# 1. CARGA DE ARCHIVO
# ---------------------------------------------------------
uploaded_file = st.file_uploader("Elige tu archivo CSV", type=['csv'])

# ---------------------------------------------------------
# 2. DEFINIR FUNCIONES DE LIMPIEZA
# ---------------------------------------------------------
localities_to_remove = [
    'CASEROS', 'CIUDADELA', 'PABLO PODESTA', 'LOMA HERMOSA', 'VILLA BOSCH', 
    'MARTIN CORONADO', 'SANTOS LUGARES', 'SAENZ PEÑA', 'EL LIBERTADOR', 
    'CIUDAD JARDIN LOMAS DEL PALOMAR', 'JOSE INGENIEROS', 'REMEDIOS DE ESCALADA', 
    '11 DE SEPTIEMBRE', 'CHURRUCA', 'VILLA RAFFO', 'NO CONSTA'
]

@st.cache_data
def procesar_archivo(file):
    # Leemos el archivo
    df = pd.read_csv(file)
    
    if 'Domicilio' not in df.columns:
        return None, "Error: No se encontró la columna 'Domicilio'"

    def limpiar_fila(domicilio_str):
        if not isinstance(domicilio_str, str):
            return pd.Series([None, None, None, None, None])
        
        # A. Separar componentes básicos
        parts = [p.strip() for p in domicilio_str.split(',')]
        if parts and parts[-1] == 'TRES DE FEBRERO':
            parts.pop()
        if parts and parts[-1] in localities_to_remove:
            parts.pop()
            
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
        
        # B. Separar Calle y Altura
        calle, altura = None, None
        if street_full:
            s = street_full
            if s.endswith('S/N'): s = s[:-3].strip()
            match = re.search(r'^(.*)\s+(\d+(?:[a-zA-Z])?)$', s)
            if match:
                calle = match.group(1).strip()
                altura = match.group(2).strip()
            else:
                if s == 'S/N' or s == '':
                     calle = None
                     altura = 'S/N'
                else:
                     calle = s
                     altura = None
                     
        # C. Limpiar Calle
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
            for pat, repl in replacements:
                calle = re.sub(pat, repl, calle)
            calle = re.sub(r'CP[:\s]\s*\d+', '', calle)
            calle = re.sub(r'\s+', ' ', calle).strip()
            
            # Si quedó solo número y no hay altura
            if re.match(r'^\d+$', calle):
                if not altura:
                    altura = calle
                    calle = None
        
        if not calle: calle = None 
        return pd.Series([calle, altura, piso, depto, cp])

    # Aplicar la función
    nuevas_columnas = df['Domicilio'].apply(limpiar_fila)
    nuevas_columnas.columns = ['Calle', 'Altura', 'Piso', 'Depto', 'Codigo_Postal']
    
    # Unir
    df_final = pd.concat([df, nuevas_columnas], axis=1)
    df_final.drop(columns=['Domicilio'], inplace=True)
    
    return df_final, None

# ---------------------------------------------------------
# 3. INTERFAZ Y EDICIÓN
# ---------------------------------------------------------
if uploaded_file is not None:
    # Procesar solo si cambia el archivo (usamos cache)
    df_procesado, error = procesar_archivo(uploaded_file)
    
    if error:
        st.error(error)
    else:
        st.success("Archivo procesado. Revisa la tabla abajo.")
        
        st.subheader("Editor de Datos")
        st.info("💡 Haz doble clic en cualquier celda para editarla. Los cambios se guardarán en el archivo descargable.")
        
        # --- AQUÍ ESTÁ LA CLAVE: st.data_editor ---
        # Permite editar el dataframe. num_rows="dynamic" permitiría agregar filas (opcional)
        df_editado = st.data_editor(df_procesado, num_rows="dynamic", use_container_width=True, height=600)
        
        st.write("---")
        
        # Botón de Descarga usando df_editado (la versión con tus cambios manuales)
        csv_buffer = df_editado.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Descargar CSV Final (Con mis ediciones)",
            data=csv_buffer,
            file_name="padron_final_editado.csv",
            mime="text/csv",
        )

else:
    st.info("Esperando archivo...")
