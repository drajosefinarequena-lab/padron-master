import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Limpiador T3F - Selector Manual", layout="wide", page_icon="🎯")
st.title("🎯 Limpiador de Direcciones (Con Selector Manual)")
st.markdown("""
**Paso 1:** Sube tu archivo.
**Paso 2:** Selecciona la columna correcta (la que tiene AV.271, RP201, etc).
**Paso 3:** La App limpiará SOLO esa columna.
""")

# --- 1. FUNCIÓN DE LIMPIEZA MEJORADA ---
def limpiar_y_separar(texto):
    if not isinstance(texto, str):
        return pd.Series([None, None, None])
    
    # Limpieza previa
    clean = texto.upper().strip()
    
    # A. ELIMINAR CÓDIGOS TIPO "AV.271-" o "RP201-"
    # Busca: Inicio + (AV/RP/PJE/C/DIAG) + Numeros + Guiones + Numeros + Guion final
    patron_codigo = r"^(AV\.|RP|PJE\.|C\.|DIAG\.|T\.)\s*\d+(\s*-\s*\d+)?\s*-\s*"
    clean = re.sub(patron_codigo, "", clean)
    
    # B. ELIMINAR CÓDIGOS TIPO "-ESC12-" o "- 14 -" en el medio
    clean = re.sub(r"\s*-\s*(ESC|EDF|TORRE)?\s*\d+\s*-\s*", " ", clean)

    # C. BUSCAR CALLE Y ALTURA
    # Estrategia: Buscar el último número sólido antes de textos como "PISO", "DPTO", "CP", "LOC"
    # Regex:
    # ^(.+?)      -> Grupo 1: Calle (Todo lo del principio)
    # \s+         -> Espacio obligatorio
    # (\d+)       -> Grupo 2: Altura (Números)
    # (\s.*)?$    -> Grupo 3: Resto (Opcional, lo que sigue)
    
    # Primero cortamos cosas obvias del final para que no confundan (CP, Localidad)
    # Si hay una coma seguida de CP o localidad, cortamos ahí virtualmente para buscar la altura antes
    corte_virtual = re.split(r",\s*(CP|LOC|CASEROS|CIUDADELA|TRES DE FEBRERO)", clean)[0]
    
    match = re.search(r"^(.+?)\s+(\d+)$", corte_virtual)
    
    if match:
        calle = match.group(1).strip()
        altura = match.group(2).strip()
        
        # Recuperamos el resto original quitando la calle y altura encontradas
        # Esto es para guardar Piso, Depto, Localidad en la 3er columna
        resto = clean.replace(calle, "").replace(altura, "", 1).strip(" -.,")
        
        # Limpieza final de calle (quitar guiones iniciales/finales)
        calle = calle.strip(" -")
        
        return pd.Series([calle, altura, resto])
    else:
        # Si no encuentra patrón Calle + Numero, devuelve todo en calle
        return pd.Series([clean, None, None])

# --- 2. INTERFAZ ---
uploaded_file = st.file_uploader("📂 Sube tu Padrón (Excel/CSV)", type=["xlsx", "csv"])

if uploaded_file:
    # Carga inteligente
    try:
        if uploaded_file.name.endswith('.csv'):
            # Probamos varios separadores por si acaso
            try:
                df = pd.read_csv(uploaded_file, encoding='latin-1', sep=None, engine='python')
            except:
                df = pd.read_csv(uploaded_file, encoding='utf-8', sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
            
        st.success(f"✅ Archivo cargado: {len(df)} filas detectadas.")
    except Exception as e:
        st.error(f"Error al leer: {e}")
        st.stop()

    # --- PASO CRÍTICO: SELECCIÓN DE COLUMNA ---
    st.divider()
    st.subheader("🕵️ Identifica la columna de Dirección")
    st.info("Mira la tabla de abajo. ¿Cuál es la columna que tiene los datos sucios (AV.271, MILITAR, etc)?")
    
    # Mostramos una muestra para que el usuario vea
    st.dataframe(df.head(3))
    
    # Selector
    todas_columnas = df.columns.tolist()
    # Intentamos adivinar inteligentemente para ponerlo por defecto
    default_idx = 0
    for i, col in enumerate(todas_columnas):
        muestras = df[col].astype(str).head(5).tolist()
        # Si alguna muestra tiene números y letras, es probable candidato
        if any(re.search(r"\d", m) and re.search(r"[a-zA-Z]", m) for m in muestras):
            default_idx = i
            break
            
    columna_elegida = st.selectbox("Selecciona la columna AQUÍ:", todas_columnas, index=default_idx)
    
    st.write(f"Has elegido procesar: **{columna_elegida}**")
    st.caption(f"Ejemplo de dato a limpiar: {df[columna_elegida].iloc[0]}")

    # --- BOTÓN DE ACCIÓN ---
    if st.button("🚀 LIMPIAR AHORA", type="primary"):
        with st.spinner(f"Limpiando {columna_elegida}..."):
            
            # 1. Aplicamos limpieza
            nuevas_cols = df[columna_elegida].astype(str).apply(limpiar_y_separar)
            nuevas_cols.columns = ['CALLE_LIMPIA', 'ALTURA', 'DETALLES_EXTRA']
            
            # 2. Unimos al original
            df_final = pd.concat([df, nuevas_cols], axis=1)
            
            # 3. Reordenamos para que lo nuevo quede al principio
            cols_fijas = ['CALLE_LIMPIA', 'ALTURA', 'DETALLES_EXTRA']
            cols_resto = [c for c in df.columns if c != columna_elegida] # Quitamos la sucia original o la dejamos al final
            df_export = df_final[cols_fijas + cols_resto]
            
            st.success("¡Listo! Mira la diferencia:")
            st.dataframe(df_export.head())
            
            # 4. Descarga
            nombre_final = "padron_limpio_ok.csv"
            csv = df_export.to_csv(index=False).encode('latin-1', errors='replace')
            
            st.download_button(
                label="📥 DESCARGAR PADRÓN CORREGIDO",
                data=csv,
                file_name=nombre_final,
                mime="text/csv"
            )

else:
    st.info("Esperando archivo...")
