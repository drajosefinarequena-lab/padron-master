import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(page_title="Limpiador de Calles Agrupadas", layout="wide")
st.title("🧹 Limpiador de Calles Agrupadas")
st.markdown("""
**Flujo de trabajo:**
1. El sistema agrupa todas las calles idénticas.
2. Revisas una por una (empezando por las más comunes).
3. Si está mal, la **renombras** (se corrige en todos los registros).
4. Si está bien, la marcas como **correcta**.
5. En ambos casos, **desaparece de la lista** para que avances.
""")

# ---------------------------------------------------------
# 1. FUNCIONES DE CARGA Y LIMPIEZA
# ---------------------------------------------------------
localities_to_remove = [
    'CASEROS', 'CIUDADELA', 'PABLO PODESTA', 'LOMA HERMOSA', 'VILLA BOSCH', 
    'MARTIN CORONADO', 'SANTOS LUGARES', 'SAENZ PEÑA', 'EL LIBERTADOR', 
    'CIUDAD JARDIN LOMAS DEL PALOMAR', 'JOSE INGENIEROS', 'REMEDIOS DE ESCALADA', 
    '11 DE SEPTIEMBRE', 'CHURRUCA', 'VILLA RAFFO', 'NO CONSTA'
]

def limpiar_domicilio_inicial(domicilio_str):
    if not isinstance(domicilio_str, str): return pd.Series([None, None])
    parts = [p.strip() for p in domicilio_str.split(',')]
    if parts and parts[-1] == 'TRES DE FEBRERO': parts.pop()
    if parts and parts[-1] in localities_to_remove: parts.pop()
    
    remaining = []
    for p in parts:
        p_upper = p.upper()
        if not (p_upper.startswith('CP:') or p_upper.startswith('PISO') or 'DEPTO' in p_upper):
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
            if s not in ['S/N', '']: calle = s
            else: altura = 'S/N'
            
    if calle:
        calle = calle.upper().replace('NO CONSTA', '').strip()
        calle = re.sub(r'\bS/N\b', '', calle).strip()
        
    return pd.Series([calle, altura])

def cargar_inteligente(file):
    """Intenta cargar el archivo manejando diferentes formatos"""
    file.seek(0)
    # Intento 1: Leer normal con encabezados
    df = pd.read_csv(file)
    
    # CASO A: Archivo Original (con Domicilio)
    if 'Domicilio' in df.columns:
        st.toast("Archivo original detectado. Procesando...")
        cols = df['Domicilio'].apply(limpiar_domicilio_inicial)
        cols.columns = ['Calle', 'Altura']
        df = pd.concat([df, cols], axis=1)
        df.drop(columns=['Domicilio'], inplace=True)
        return df

    # CASO B: Archivo Procesado con encabezados correctos
    if 'Calle' in df.columns:
        return df

    # CASO C: Archivo sin encabezados (Raw)
    # Si llegamos aquí, probablemente leyó la primera fila como título y 'Calle' no existe.
    # Recargamos sin header.
    file.seek(0)
    df_raw = pd.read_csv(file, header=None)
    
    # Intentamos adivinar las columnas según la cantidad
    # Asumimos estructura: Apellido, Nombre, Matricula, F_Nac, Calle, Altura, Piso, Depto
    if len(df_raw.columns) >= 5:
        st.toast("Archivo sin cabeceras detectado. Asignando nombres...")
        nuevos_nombres = [f"Col_{i}" for i in range(len(df_raw.columns))]
        
        # Mapeo manual basado en tu archivo anterior
        mapa = {0: 'Apellido', 1: 'Nombre', 2: 'Matricula', 3: 'F_Nacimiento', 4: 'Calle', 5: 'Altura', 6: 'Piso', 7: 'Depto'}
        
        for i, nombre in mapa.items():
            if i < len(nuevos_nombres):
                nuevos_nombres[i] = nombre
                
        df_raw.columns = nuevos_nombres
        return df_raw

    # Si nada funciona, devolvemos lo que hay, pero fallará si no hay columna Calle
    return df

# ---------------------------------------------------------
# 2. GESTIÓN DEL ESTADO
# ---------------------------------------------------------
if 'df' not in st.session_state:
    st.session_state.df = None
if 'calles_revisadas' not in st.session_state:
    st.session_state.calles_revisadas = set()

# ---------------------------------------------------------
# 3. BARRA LATERAL
# ---------------------------------------------------------
with st.sidebar:
    st.header("1. Cargar Archivo")
    uploaded_file = st.file_uploader("Sube tu CSV", type=['csv'])
    
    if uploaded_file is not None and st.session_state.df is None:
        try:
            df_cargado = cargar_inteligente(uploaded_file)
            
            if 'Calle' not in df_cargado.columns:
                st.error("Error: No se pudo identificar la columna 'Calle'. Verifica el formato.")
            else:
                st.session_state.df = df_cargado
                st.success("¡Archivo cargado!")
                st.rerun()
            
        except Exception as e:
            st.error(f"Error crítico al cargar: {e}")

    st.write("---")
    st.header("3. Descargar Resultado")
    if st.session_state.df is not None:
        csv = st.session_state.df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Bajar CSV Final", csv, "padron_limpio.csv", "text/csv")
        
    if st.button("🔄 Reiniciar todo"):
        st.session_state.df = None
        st.session_state.calles_revisadas = set()
        st.rerun()

# ---------------------------------------------------------
# 4. ÁREA PRINCIPAL
# ---------------------------------------------------------
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Asegurar que Calle sea string y llenar nulos
    df['Calle'] = df['Calle'].astype(str).replace('nan', 'SIN NOMBRE').fillna('SIN NOMBRE')
    
    # Calcular conteos
    conteo_calles = df['Calle'].value_counts()
    calles_pendientes = [c for c in conteo_calles.index if c not in st.session_state.calles_revisadas]
    
    total_calles = len(conteo_calles)
    restantes = len(calles_pendientes)
    
    # Barra de progreso
    if total_calles > 0:
        progreso = 1 - (restantes / total_calles)
        st.progress(progreso)
    st.metric("Calles pendientes", f"{restantes}", delta=f"-{total_calles - restantes} revisadas")

    if restantes == 0:
        st.balloons()
        st.success("¡Felicidades! Has revisado todas las calles agrupadas.")
    else:
        # Tomar la primera calle pendiente
        calle_actual = calles_pendientes[0]
        count_actual = conteo_calles[calle_actual]
        
        st.divider()
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🛠️ Editar Calle")
            st.info(f"Estás revisando: **{calle_actual}**")
            st.caption(f"Aparece en {count_actual} domicilios.")
            
            # Formulario para editar
            with st.form("form_edicion"):
                nuevo_nombre = st.text_input("Corrección:", value=calle_actual)
                
                col_btn1, col_btn2 = st.columns(2)
                confirmar = col_btn1.form_submit_button("✅ Guardar", type="primary")
                ignorar = col_btn2.form_submit_button("⏭️ Ignorar/Saltar")
                
                if confirmar:
                    if nuevo_nombre != calle_actual:
                        # Aplicar cambio masivo
                        st.session_state.df.loc[st.session_state.df['Calle'] == calle_actual, 'Calle'] = nuevo_nombre
                        st.toast(f"Cambio aplicado: {calle_actual} ➝ {nuevo_nombre}")
                        # Marcar el NUEVO nombre como revisado para que no vuelva a salir
                        st.session_state.calles_revisadas.add(nuevo_nombre)
                    else:
                        st.toast("Calle marcada como correcta.")
                    
                    # Marcar el viejo como revisado
                    st.session_state.calles_revisadas.add(calle_actual)
                    st.rerun()
                
                if ignorar:
                    st.session_state.calles_revisadas.add(calle_actual)
                    st.rerun()
                
        with col2:
            st.subheader("📋 Registros afectados")
            st.caption("Muestra de dónde aparece esta calle:")
            # Filtramos y mostramos columnas relevantes
            cols_to_show = [c for c in ['Apellido', 'Nombre', 'Calle', 'Altura'] if c in df.columns]
            st.dataframe(df[df['Calle'] == calle_actual][cols_to_show].head(10), use_container_width=True)

else:
    st.info("👈 Sube un archivo CSV en el menú lateral para comenzar.")
