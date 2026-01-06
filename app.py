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
# 1. FUNCIONES DE CARGA Y LIMPIEZA INICIAL
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
    
    # Separación básica inicial (solo para tener Calle y Altura separadas)
    # No limpiamos el nombre "a fondo" aquí para dejar que el usuario lo revise agrupado
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

# ---------------------------------------------------------
# 2. GESTIÓN DEL ESTADO (SESSION STATE)
# ---------------------------------------------------------
if 'df' not in st.session_state:
    st.session_state.df = None
if 'calles_revisadas' not in st.session_state:
    st.session_state.calles_revisadas = set()

# ---------------------------------------------------------
# 3. BARRA LATERAL (CARGA Y DESCARGA)
# ---------------------------------------------------------
with st.sidebar:
    st.header("1. Cargar Archivo")
    uploaded_file = st.file_uploader("Sube tu CSV", type=['csv'])
    
    if uploaded_file is not None and st.session_state.df is None:
        try:
            df_temp = pd.read_csv(uploaded_file)
            
            # Si es el archivo original, procesamos la separación inicial
            if 'Domicilio' in df_temp.columns and 'Calle' not in df_temp.columns:
                st.info("Separando calles y alturas iniciales...")
                cols = df_temp['Domicilio'].apply(limpiar_domicilio_inicial)
                cols.columns = ['Calle', 'Altura']
                # Mantenemos columnas extra si existen
                df_temp = pd.concat([df_temp, cols], axis=1)
                df_temp.drop(columns=['Domicilio'], inplace=True)
            
            st.session_state.df = df_temp
            st.success("¡Archivo cargado!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error al cargar: {e}")

    st.write("---")
    st.header("3. Descargar Resultado")
    if st.session_state.df is not None:
        csv = st.session_state.df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Bajar CSV Final",
            csv,
            "padron_limpio.csv",
            "text/csv"
        )
        
    if st.button("🔄 Reiniciar todo"):
        st.session_state.df = None
        st.session_state.calles_revisadas = set()
        st.rerun()

# ---------------------------------------------------------
# 4. ÁREA PRINCIPAL DE TRABAJO
# ---------------------------------------------------------
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Filtrar calles nulas
    df['Calle'] = df['Calle'].fillna('SIN NOMBRE')
    
    # Calcular conteos de calles, excluyendo las ya revisadas
    conteo_calles = df['Calle'].value_counts()
    calles_pendientes = [c for c in conteo_calles.index if c not in st.session_state.calles_revisadas]
    
    total_calles = len(conteo_calles)
    restantes = len(calles_pendientes)
    progreso = 1 - (restantes / total_calles) if total_calles > 0 else 0
    
    st.progress(progreso)
    st.write(f"Calles revisadas: **{total_calles - restantes}** / {total_calles} | Pendientes: **{restantes}**")

    if restantes == 0:
        st.success("¡Felicidades! Has revisado todas las calles agrupadas.")
    else:
        # --- SELECCIÓN DE CALLE ---
        # Por defecto tomamos la primera (la más frecuente)
        calle_actual = calles_pendientes[0]
        count_actual = conteo_calles[calle_actual]
        
        st.write("---")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Calle a revisar")
            st.info(f"Nombre actual: **{calle_actual}**")
            st.write(f"Aparece en **{count_actual}** registros.")
            
            # Opción de cambiar el nombre
            nuevo_nombre = st.text_input("Editar nombre:", value=calle_actual)
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar / Guardar", type="primary"):
                # Si el nombre cambió
                if nuevo_nombre != calle_actual:
                    # Actualizar en el DataFrame
                    st.session_state.df.loc[st.session_state.df['Calle'] == calle_actual, 'Calle'] = nuevo_nombre
                    st.toast(f"Renombrado: {calle_actual} -> {nuevo_nombre}")
                else:
                    st.toast(f"Marcado como correcto: {calle_actual}")
                
                # Marcar como revisada (usamos el nombre original para sacarla de la lista de pendientes)
                st.session_state.calles_revisadas.add(calle_actual)
                # También agregamos el nuevo nombre a revisadas para que no vuelva a aparecer
                st.session_state.calles_revisadas.add(nuevo_nombre)
                st.rerun()

            if c2.button("Ignorar / Saltar"):
                st.session_state.calles_revisadas.add(calle_actual)
                st.rerun()
                
        with col2:
            st.subheader("Vista previa de registros")
            # Mostrar hasta 10 ejemplos de esta calle
            ejemplos = df[df['Calle'] == calle_actual].head(10)
            st.dataframe(ejemplos, use_container_width=True)

else:
    st.info("Sube un archivo desde el menú lateral para comenzar.")
