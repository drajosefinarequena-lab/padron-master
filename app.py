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

st.set_page_config(page_title="Lista 4 - Padrón 2026", page_icon="✌️", layout="wide")

# --- CONEXIÓN GOOGLE SHEETS PARA AUDITORÍA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def registrar_evento(nombre, localidad, accion, detalle):
    try:
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ip = requests.get('https://api.ipify.org', timeout=2).text
        nueva_fila = pd.DataFrame([{
            "Fecha": ahora, "Usuario": nombre, "Célula/Localidad": localidad, 
            "Acción": accion, "Término Buscado": detalle, "Ubicación (IP)": ip
        }])
        df_log = conn.read(worksheet="resultados")
        conn.update(worksheet="resultados", data=pd.concat([df_log, nueva_fila], ignore_index=True))
    except: pass

# --- PERSISTENCIA DE SESIÓN ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "busqueda_activa" not in st.session_state: st.session_state.busqueda_activa = ""

# --- PANTALLA DE ACCESO ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align:center;'>✌️ LISTA 4 - INGRESO</h1>", unsafe_allow_html=True)
    nom = st.text_input("NOMBRE Y APELLIDO:")
    loc = st.selectbox("LOCALIDAD:", ["---"] + list(LOCALIDADES_CLAVES.keys()))
    pw = st.text_input("CLAVE:", type="password")
    
    if st.button("ACCEDER"):
        if pw == CLAVE_ADMIN or (loc in LOCALIDADES_CLAVES and pw == LOCALIDADES_CLAVES[loc] and nom != ""):
            st.session_state.autenticado = True
            st.session_state.nombre = nom if nom else "ADMIN"
            st.session_state.localidad = loc
            registrar_evento(st.session_state.nombre, loc, "INGRESO", "Sesión iniciada")
            st.rerun()
        else: st.error("Datos incorrectos")
else:
    # --- BUSCADOR ---
    st.header(f"Padrón 2026 - Usuario: {st.session_state.nombre}")

    @st.cache_data
    def cargar_datos_excel():
        try:
            # Forzamos la carga del nuevo archivo Excel
            df = pd.read_excel("PADRON2026.xlsx", engine='openpyxl')
            # Filtramos columnas esenciales para que la tabla no sea gigante
            visibles = [c for c in df.columns if any(x in str(c).upper() for x in ['DNI', 'MATRICULA', 'NOMBRE', 'APELLIDO', 'DIRECCION', 'CALLE'])]
            return df[visibles].fillna('')
        except Exception as e:
            st.error(f"Error cargando PADRON2026.xlsx: {e}")
            return None

    padron = cargar_datos_excel()

    if padron is not None:
        # Formulario para evitar recargas accidentales
        with st.form("panel_busqueda"):
            query = st.text_input("🔎 BUSCÁ POR CALLE, APELLIDO O DNI:", value=st.session_state.busqueda_activa)
            enviar = st.form_submit_button("EJECUTAR BÚSQUEDA")
            
            if enviar and query:
                st.session_state.busqueda_activa = query
                registrar_evento(st.session_state.nombre, st.session_state.localidad, "BÚSQUEDA", query)
                
                termino = query.strip().upper()
                mask = padron.astype(str).apply(lambda row: row.str.upper().str.contains(termino)).any(axis=1)
                resultados = padron[mask]
                
                if not resultados.empty:
                    st.success(f"Se encontraron **{len(resultados)}** resultados para '{query}'.")
                    st.dataframe(resultados, use_container_width=True, height=600)
                else:
                    st.warning("No se encontraron resultados.")

    if st.button("CERRAR SESIÓN"):
        st.session_state.autenticado = False
        st.session_state.busqueda_activa = ""
        st.rerun()
