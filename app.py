import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Reparador de Archivo T3F", layout="wide", page_icon="🩹")
st.title("🩹 Reparador de Archivo CSV Roto")
st.markdown("""
**Diagnóstico:** Tu archivo original tiene la dirección partida en 3 columnas distintas (por culpa de las comas).
**Solución:** Esta App pegará los pedazos de nuevo y luego limpiará la dirección.
""")

# --- 1. LÓGICA DE RECONSTRUCCIÓN ---
def reparar_y_limpiar(row):
    # Unimos las columnas sospechosas para reconstruir la dirección completa
    # Usamos las columnas que detectamos en el análisis: ACCESO, 4, y la larga del final
    
    # Tomamos todo como texto
    parte1 = str(row.get('ACCESO', ''))
    parte2 = str(row.get('4', ''))
    # Buscamos la columna larga que empieza con guion o monoblock
    cols_largas = [c for c in row.index if 'MONOBLOCK' in str(c) or 'DEPTO' in str(c)]
    parte3 = str(row[cols_largas[0]]) if cols_largas else ''
    
    # Reconstruimos: "AV.271" + " " + "-" + "MILITAR 3050..."
    direccion_full = f"{parte1} {parte2} {parte3}".replace("nan", "").strip()
    
    return procesar_direccion_final(direccion_full)

def procesar_direccion_final(texto):
    clean = texto.upper().strip()
    
    # A. Limpieza de códigos (AV.271, RP201)
    # Borramos prefijos basura
    clean = re.sub(r"^(AV\.|RP|PJE\.|C\.|DIAG\.|T\.)\s*\d+.*?-", "", clean)
    clean = re.sub(r"^\d+\s*-\s*", "", clean) # Borrar numeros sueltos al inicio
    
    # B. Separar Calle y Altura
    # Cortamos antes de CP, Loc, etc
    corte = re.split(r"[,;]\s*(CP|LOC|CASEROS|CIUDADELA|TRES DE FEBRERO)", clean)[0]
    
    # Buscamos Calle + Numero
    match = re.search(r"^(.+?)\s+(\d+)$", corte)
    
    if match:
        calle = match.group(1).strip(" -")
        altura = match.group(2).strip()
        resto = clean.replace(calle, "").replace(altura, "", 1).strip(" -.,")
        return pd.Series([calle, altura, resto])
    else:
        return pd.Series([clean, None, None])

# --- 2. INTERFAZ ---
uploaded_file = st.file_uploader("📂 Sube el archivo 'padron_sin_codigos.csv' (o el original roto)", type=["csv"])

if uploaded_file:
    try:
        # Leemos el archivo tal cual viene
        df = pd.read_csv(uploaded_file, encoding='latin-1', sep=None, engine='python')
        st.success(f"Archivo cargado. Detectando columnas rotas...")
    except:
        st.error("Error leyendo archivo.")
        st.stop()

    # Verificamos si tiene las columnas rotas
    col_sospechosa = [c for c in df.columns if 'MONOBLOCK' in c or 'DEPTO' in c]
    
    if 'ACCESO' in df.columns and col_sospechosa:
        st.warning("⚠️ ¡Detecté el problema! La dirección está partida en las columnas 'ACCESO' y la del final.")
        
        if st.button("🩹 REPARAR Y LIMPIAR AHORA", type="primary"):
            with st.spinner("Pegando columnas y extrayendo direcciones..."):
                
                # Aplicamos la reparación fila por fila
                nuevas = df.apply(reparar_y_limpiar, axis=1)
                nuevas.columns = ['CALLE_LIMPIA', 'ALTURA', 'DETALLES']
                
                # Unimos al original
                df_final = pd.concat([df, nuevas], axis=1)
                
                # Seleccionamos lo importante
                cols_mostrar = ['CALLE_LIMPIA', 'ALTURA', 'DETALLES']
                # Tratamos de conservar nombre/apellido si existen
                cols_nombres = [c for c in df.columns if 'RODRIGUEZ' in c or 'CLAUDIA' in c or 'APELLIDO' in c.upper()]
                
                df_export = df_final[cols_mostrar + cols_nombres]
                
                st.success("¡Reparación exitosa! Mira:")
                st.dataframe(df_export.head())
                
                # Descarga
                csv = df_export.to_csv(index=False).encode('latin-1', errors='replace')
                st.download_button("📥 DESCARGAR BASE REPARADA", csv, "padron_reparado.csv", "text/csv")
    
    else:
        st.info("No detecto las columnas rotas específicas ('ACCESO', 'MONOBLOCK'). Quizás este archivo tiene otro formato.")
        st.dataframe(df.head())

else:
    st.info("Sube el archivo para analizarlo.")
