# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import requests
import os

# 1. CONFIGURACIÓN DE SEGURIDAD
LOCALIDADES_CLAVES = {
    "CASEROS": "caseros2026", "CIUDADELA": "ciudadela2026", "BARRIO_EJERCITO": "barrioejercito2026",
    "VILLA_BOSCH": "villabosch2026", "MARTIN_CORONADO": "martincoronado2026", "CIUDAD_JARDIN": "ciudadjardin2026",
    "SANTOS_LUGARES": "santoslugares2026", "SAENZ_PEÑA": "saenzpeña2026", "PODESTA": "podesta2026",
    "CHURRUCA": "churruca2026", "EL_LIBERTADOR": "ellibertador2026", "LOMA_HERMOSA": "lomahermosa2026"
}
CLAVE_ADMIN = "josefina3f_admin"

st.set_page_config(page_title="Lista 4 - Padrón 2026", layout="wide")

# --- CONEXIÓN GOOGLE SHEETS PARA AUDITORÍA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def registrar_en_google(nombre, localidad, busqueda):
    try:
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ip = requests.get('https://api.ipify.org', timeout=2).text
        nueva_fila = pd.DataFrame([{"Fecha": ahora, "Usuario": nombre, "Célula/Localidad": localidad, "Acción": "BÚSQUEDA", "Término Buscado": busqueda, "Ubicación (IP)": ip}])
        df_log = conn.read(worksheet="resultados")
        conn.update(worksheet="resultados", data=pd.concat([df_log, nueva_fila], ignore_index=True))
    except: pass

# --- ACCESO ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align:center;'>✌️ LISTA 4 - INGRESO</h1>", unsafe_allow_html=True)
    nom = st.text_input("NOMBRE:")
    loc = st.selectbox("LOCALIDAD:", ["---"] + list(LOCALIDADES_CLAVES.keys()))
    pw = st.text_input("CLAVE:", type="password")
    if st.button("INGRESAR"):
        if pw == CLAVE_ADMIN or (loc in LOCALIDADES_CLAVES and pw == LOCALIDADES_CLAVES[loc] and nom != ""):
            st.session_state.autenticado = True
            st.session_state.nombre = nom
            st.session_state.localidad = loc
            st.rerun()
else:
    # --- CARGA EXCLUSIVA DE PADRON2026.XLSX ---
    @st.cache_data
    def cargar_datos():
        try:
            # Forzamos la lectura del Excel para que veas los 107 de Sabatini
            df = pd.read_excel("PADRON2026.xlsx", engine='openpyxl')
            # Solo columnas básicas
            visibles = [c for c in df.columns if any(x in str(c).upper() for x in ['DNI', 'MATRICULA', 'NOMBRE', 'APELLIDO', 'DIRECCION', 'CALLE'])]
            return df[visibles].fillna('')
        except Exception as e:
            st.error(f"Error técnico: Asegurate de que el archivo se llame PADRON2026.xlsx. Detalle: {e}")
            return None

    padron = cargar_datos()

    if padron is not None:
        st.sidebar.write(f"📊 Registros totales: {len(padron)}")
        busqueda = st.text_input("🔎 BUSCÁ POR CALLE O APELLIDO (Escribí Sabatini):")
        
        if busqueda:
            registrar_en_google(st.session_state.nombre, st.session_state.localidad, busqueda)
            termino = busqueda.strip().upper()
            mask = padron.astype(str).apply(lambda row: row.str.upper().str.contains(termino)).any(axis=1)
            resultados = padron[mask]
            
            if not resultados.empty:
                st.success(f"Se encontraron **{len(resultados)}** resultados.")
                st.dataframe(resultados, use_container_width=True, height=600)
            else:
                st.warning("No se encontraron coincidencias.")

    if st.button("CERRAR SESIÓN"):
        st.session_state.autenticado = False
        st.rerun()
