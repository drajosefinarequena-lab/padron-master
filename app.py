import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Padrón Unificado T3F", layout="wide")
st.title("📍 Padrón Unificado - Tres de Febrero")

# --- 1. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        # Intentamos leer el archivo
        df = pd.read_csv("datos.csv", encoding='latin-1', sep=None, engine='python')
        return df
    except:
        return None

# --- 2. LA APLANADORA (Función de Fuerza Bruta) ---
def unificar_a_la_fuerza(texto):
    if not isinstance(texto, str): return ""
    # 1. Normalización básica
    calle = texto.upper().strip()
    calle = calle.replace(".", " ") # C. GARDEL -> C  GARDEL
    
    # 2. REGLAS DE ORO (Si contiene la palabra clave, se reescribe TOTALMENTE)
    # El orden importa: las reglas más específicas van primero.

    # --- CASO SAN MARTÍN (Distinguir Boulevard de Avenida) ---
    if "SAN MARTIN" in calle:
        if "BV" in calle or "BOULEVARD" in calle or "B AL" in calle: # "B AL" por si dice B AL RIO
            return "BOULEVARD SAN MARTIN"
        else:
            return "AV SAN MARTIN"

    # --- CASOS CRÍTICOS (GARDEL, MITRE, ETC) ---
    # Si aparece "GARDEL" (sea C. Gardel, Carlos Gardel, Gardel Carlos) -> CARLOS GARDEL
    if "GARDEL" in calle: return "CARLOS GARDEL"
    
    # Si aparece "MITRE" (Bme Mitre, B. Mitre, Bartolome Mitre) -> BARTOLOME MITRE
    if "MITRE" in calle: return "BARTOLOME MITRE"
    
    if "ANCHORDO" in calle: return "DR ENRIQUE ANCHORDOQUI" # Agarra Anchordoqui, Anchordoquy...
    
    if "ALVEAR" in calle: return "MARCELO T DE ALVEAR"
    
    if "URQUIZA" in calle: return "URQUIZA"
    
    if "ROSAS" in calle and "JUAN" in calle: return "JUAN MANUEL DE ROSAS" # Para no confundir con otras Rosas
    if "ROSAS" in calle and "BRIG" in calle: return "JUAN MANUEL DE ROSAS"
    
    if "GLADIOLO" in calle: return "DE LOS GLADIOLOS"
    
    if "PELLEGRINI" in calle: return "CARLOS PELLEGRINI"
    if "PELEGRINI" in calle: return "CARLOS PELLEGRINI" # Por si escribieron mal
    
    if "YRIGOYEN" in calle or "IRIGOYEN" in calle: return "HIPOLITO YRIGOYEN"
    
    if "PAZ" in calle and ("GRAL" in calle or "GENERAL" in calle): return "AV GENERAL PAZ"
    
    if "AMARILLO" in calle and ("CERRO" in calle or "C " in calle): return "CERRO AMARILLO"
    
    if "BESARES" in calle: return "BESARES" # A veces ponen "Gral Besares"
    
    # 3. SI NO CUMPLE NINGUNA REGLA DE ORO, LIMPIEZA GENÉRICA
    # Quitamos prefijos comunes para el resto de las calles
    basura = ["AV.", "AV ", "AVENIDA ", "CALLE ", "DR.", "DR ", "GRAL.", "GRAL ", "PJE.", "PJE "]
    for b in basura:
        if calle.startswith(b):
            calle = calle.replace(b, "")
            
    return calle.strip()

# --- 3. EXTRACCIÓN ---
def procesar_direccion(texto):
    if not isinstance(texto, str): return None, None, None
    # Buscamos texto + numeros
    match = re.search(r"^([A-Z\s\.\d\ñ\Ñ]+?)\s+(\d+)", texto.upper())
    if match:
        raw = match.group(1).strip()
        altura = int(match.group(2))
        # Aplicamos la Aplanadora
        clean = unificar_a_la_fuerza(raw)
        return raw, altura, clean
    return None, None, None

# --- INICIO APP ---
df = cargar_datos()

if df is not None:
    # Procesar
    if 'CALLE_UNIFICADA' not in df.columns:
        with st.spinner('Aplicando reglas de unificación...'):
            datos = df['Domicilio'].apply(process_address_lambda_wrapper := lambda x: pd.Series(procesar_direccion(x)))
            df['CALLE_ORIGINAL'] = datos[0]
            df['ALTURA'] = datos[1]
            df['CALLE_UNIFICADA'] = datos[2]
            df = df.dropna(subset=['CALLE_UNIFICADA'])

    st.success(f"✅ Base lista: {len(df)} vecinos.")
    
    # --- PRUEBA DE FUEGO ---
    st.markdown("### 🔎 Prueba de Unificación")
    st.markdown("Escribe 'GARDEL' o 'MITRE' abajo para ver si se unificaron.")
    
    col_search, col_result = st.columns(2)
    with col_search:
        filtro_prueba = st.text_input("Buscar calle (Ej: MITRE):").upper()
    
    if filtro_prueba:
        # Filtramos por el nombre original para ver qué variantes había
        resultados = df[df['CALLE_ORIGINAL'].str.contains(filtro_prueba, na=False)]
        if not resultados.empty:
            st.write(f"Se encontraron **{len(resultados)}** registros originales con '{filtro_prueba}'.")
            st.write("Mira la columna **CALLE_UNIFICADA**. Debería decir lo mismo para todos.")
            
            # Mostramos tabla resumen
            st.dataframe(resultados[['CALLE_ORIGINAL', 'CALLE_UNIFICADA', 'ALTURA']].head(20))
        else:
            st.warning("No encontré esa calle en la base original.")
            
    st.divider()
    
    # --- EL BUSCADOR PRINCIPAL ---
    st.subheader("📍 Buscador Operativo")
    
    tab1, tab2 = st.tabs(["🏠 Por Calle", "👤 Por Persona"])
    
    with tab1:
        # Usamos la lista de calles UNIFICADAS para el selector
        lista_calles = sorted(df['CALLE_UNIFICADA'].unique())
        calle_input = st.selectbox("Selecciona Calle:", lista_calles)
        altura_input = st.number_input("Altura:", step=100)
        
        if calle_input:
            final = df[df['CALLE_UNIFICADA'] == calle_input]
            
            if altura_input > 0:
                final = final[(final['ALTURA'] >= altura_input - 300) & (final['ALTURA'] <= altura_input + 300)]
                final['Distancia'] = abs(final['ALTURA'] - altura_input)
                final = final.sort_values('Distancia')
            else:
                final = final.sort_values('ALTURA')
                
            st.write(f"Vecinos encontrados: {len(final)}")
            st.dataframe(final[['Apellido', 'Nombre', 'CALLE_UNIFICADA', 'ALTURA', 'Domicilio']])

    with tab2:
        apellido = st.text_input("Apellido:")
        if apellido:
            res = df[df['Apellido'].str.contains(apellido.upper(), na=False)]
            st.dataframe(res[['Apellido', 'Nombre', 'CALLE_UNIFICADA', 'ALTURA']])

else:
    st.error("⚠️ Sube datos.csv a GitHub")
