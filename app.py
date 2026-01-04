import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Separador T3F - Códigos Catastrales", layout="wide", page_icon="🏗️")
st.title("🏗️ Separador de Direcciones (Modo Tres de Febrero)")
st.markdown("""
Esta herramienta está calibrada para eliminar códigos catastrales como **AV.271-**, **RP201-**, **PJE.12-** y detectar la altura real al final.
""")

# --- 1. FUNCIÓN DE LIMPIEZA QUIRÚRGICA ---
def limpiar_y_separar(texto):
    if not isinstance(texto, str):
        return pd.Series([None, None, None])
    
    # Normalizamos
    original = texto.upper().strip()
    clean = original

    # PASO A: ELIMINAR PREFIJOS CATASTRALES (La parte difícil)
    # Buscamos patrones como:
    # "AV.271- "
    # "RP201- 283 - "
    # "PJE.12- "
    # Regex explicada:
    # ^(AV\.|RP|PJE\.|C\.)   -> Empieza con AV., RP, PJE. o C.
    # \s*\d+                 -> Seguido de números (271, 201)
    # (\s*-\s*\d+)?          -> Opcionalmente otro guion y numero (el 283 o 618)
    # \s*-\s* -> Termina con un guion separador
    
    patron_basura = r"^(AV\.|RP|PJE\.|C\.|DIAG\.)\s*\d+(\s*-\s*\d+)?\s*-\s*"
    clean = re.sub(patron_basura, "", clean)

    # PASO B: ELIMINAR CÓDIGOS INTERNOS (Ej: "-ESC12-")
    clean = re.sub(r"\s*-\s*ESC\d+\s*-\s*", " ", clean)

    # PASO C: EXTRAER CALLE Y ALTURA (Del texto ya limpio)
    # Buscamos el último número antes de una coma, un "CP", o el final
    # Ejemplo: "MILITAR 3050, CP..." -> Calle: MILITAR, Num: 3050
    
    match = re.search(r"^(.+?)\s+(\d+)(\s*[,;].*|\s*CP.*|\s*LOC.*)?$", clean)
    
    if match:
        calle = match.group(1).strip()
        altura = match.group(2).strip()
        
        # El resto lo tomamos del original para no perder el CP o localidad
        # Buscamos dónde termina la altura en el original para sacar el resto
        resto = ""
        if match.group(3):
            resto = match.group(3).strip(",; ")
        
        # Limpieza final de la calle (quitar guiones sobrantes)
        calle = calle.replace("-", " ").strip()
        
        return pd.Series([calle, altura, resto])
    else:
        # Si falla, devolvemos lo que pudimos limpiar en la primera columna
        return pd.Series([clean, None, None])

# --- 2. INTERFAZ ---
uploaded_file = st.file_uploader("Sube tu archivo con códigos (CSV/Excel)", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='latin-1', sep=None, engine='python')
        else:
            df = pd.read_excel(uploaded_file)
        st.success(f"Cargado: {len(df)} registros.")
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    cols = df.columns.tolist()
    col_dom = next((c for c in cols if 'DOMICILIO' in c.upper() or 'DIRECCION' in c.upper()), cols[0])
    
    st.info(f"Procesando columna: **{col_dom}**")
    
    # VISTA PREVIA DE UN CASO DIFÍCIL (Para que veas si funciona antes de procesar todo)
    ejemplo = df[col_dom].iloc[0]
    st.caption(f"Ejemplo del primer dato crudo: {ejemplo}")

    if st.button("🚀 LIMPIAR CÓDIGOS Y SEPARAR", type="primary"):
        with st.spinner("Eliminando AV.271, RP201 y separando alturas..."):
            
            # Aplicamos la función
            nuevas = df[col_dom].apply(limpiar_y_separar)
            nuevas.columns = ['CALLE_LIMPIA', 'ALTURA', 'DETALLES']
            
            # Unimos
            df_final = pd.concat([df, nuevas], axis=1)
            
            # Ordenamos columnas para Excel
            cols_out = ['Apellido', 'Nombre', 'CALLE_LIMPIA', 'ALTURA', 'DETALLES']
            # Agregamos las que existan en el original
            cols_out = [c for c in cols_out if c in df_final.columns] 
            # Agregamos el resto
            cols_out += [c for c in df_final.columns if c not in cols_out]
            
            df_export = df_final[cols_out]
            
            st.balloons()
            
            # MOSTRAR RESULTADOS
            st.subheader("Verificación de Resultados")
            st.write("Fíjate en las columnas 'CALLE_LIMPIA' y 'ALTURA'.")
            st.dataframe(df_export[[col_dom, 'CALLE_LIMPIA', 'ALTURA']].head(10))
            
            # DESCARGA
            csv = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 DESCARGAR BASE LIMPIA",
                data=csv,
                file_name="padron_sin_codigos.csv",
                mime="text/csv"
            )

else:
    st.info("Sube el archivo.")
