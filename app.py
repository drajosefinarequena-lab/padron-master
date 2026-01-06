import pandas as pd
import re
from google.colab import drive

# ---------------------------------------------------------
# 1. CONECTAR GOOGLE DRIVE
# ---------------------------------------------------------
print("Conectando con Google Drive...")
drive.mount('/content/drive')

# ---------------------------------------------------------
# 2. CARGAR EL ARCHIVO
# ---------------------------------------------------------
# Asegúrate de haber subido 'datos.csv' a la carpeta de archivos de Colab
print("Cargando archivo datos.csv...")
try:
    df = pd.read_csv('datos.csv')
except FileNotFoundError:
    print("ERROR: No se encontró 'datos.csv'. Por favor súbelo al panel de la izquierda.")
    raise

# ---------------------------------------------------------
# 3. DEFINIR FUNCIONES DE LIMPIEZA
# ---------------------------------------------------------
localities_to_remove = [
    'CASEROS', 'CIUDADELA', 'PABLO PODESTA', 'LOMA HERMOSA', 'VILLA BOSCH', 
    'MARTIN CORONADO', 'SANTOS LUGARES', 'SAENZ PEÑA', 'EL LIBERTADOR', 
    'CIUDAD JARDIN LOMAS DEL PALOMAR', 'JOSE INGENIEROS', 'REMEDIOS DE ESCALADA', 
    '11 DE SEPTIEMBRE', 'CHURRUCA', 'VILLA RAFFO', 'NO CONSTA'
]

def procesar_domicilio_completo(domicilio_str):
    """
    Toma la cadena completa de domicilio y devuelve una Serie con:
    [Calle, Altura, Piso, Depto, Codigo_Postal]
    """
    if not isinstance(domicilio_str, str):
        return pd.Series([None, None, None, None, None])
    
    # --- PASO A: Separar componentes básicos ---
    parts = [p.strip() for p in domicilio_str.split(',')]
    
    # Eliminar 'TRES DE FEBRERO' del final
    if parts and parts[-1] == 'TRES DE FEBRERO':
        parts.pop()
    
    # Eliminar Localidad del final
    if parts and parts[-1] in localities_to_remove:
        parts.pop()
        
    # Buscar CP, Piso, Depto en las partes restantes
    cp = None
    piso = None
    depto = None
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
            
    # Reconstruir la parte de la calle
    street_full = ", ".join(remaining).strip()
    
    # --- PASO B: Separar Calle y Altura ---
    calle = None
    altura = None
    
    if street_full:
        # Quitar S/N del final para que no confunda
        s = street_full
        if s.endswith('S/N'):
            s = s[:-3].strip()
        
        # Buscar número al final
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
                 altura = None # Asumimos que es solo nombre de calle sin altura
                 
    # --- PASO C: Limpiar el nombre de la Calle ---
    if calle:
        # Normalizar
        calle = calle.upper()
        calle = calle.replace('NO CONSTA', '')
        calle = re.sub(r'\bS/N\b', '', calle)
        
        # Correcciones específicas
        replacements = [
            (r'\bAV\.', 'AVENIDA'),
            (r'\bAV\b', 'AVENIDA'),
            (r'\bGRAL\.', 'GENERAL'),
            (r'\bGRAL\b', 'GENERAL'),
            (r'\bTTE\.', 'TENIENTE'),
            (r'\bDR\.', 'DOCTOR'),
            (r'\bPJE\.', 'PASAJE'),
            (r'\b3 DE FEB\b', '3 DE FEBRERO'),
            (r'\bJ\.\s*F\.\s*KENNEDY\b', 'JOHN F. KENNEDY'),
        ]
        for pat, repl in replacements:
            calle = re.sub(pat, repl, calle)
            
        # Eliminar restos de CP si quedaron pegados
        calle = re.sub(r'CP[:\s]\s*\d+', '', calle)
        # Quitar espacios dobles
        calle = re.sub(r'\s+', ' ', calle).strip()
        
        # Validación final: Si la calle quedó siendo solo un número (ej. "15") y no hay altura
        # asumimos que ese número ERA la altura
        if re.match(r'^\d+$', calle):
            if not altura:
                altura = calle
                calle = None
    
    if not calle:
        calle = None 
        
    return pd.Series([calle, altura, piso, depto, cp])

# ---------------------------------------------------------
# 4. EJECUTAR PROCESAMIENTO
# ---------------------------------------------------------
print("Procesando domicilios (esto puede tardar unos segundos)...")
nuevas_columnas = df['Domicilio'].apply(procesar_domicilio_completo)
nuevas_columnas.columns = ['Calle', 'Altura', 'Piso', 'Depto', 'Codigo_Postal']

# Unir todo
df_final = pd.concat([df, nuevas_columnas], axis=1)
# Eliminar la columna vieja Domicilio
df_final.drop(columns=['Domicilio'], inplace=True)

# ---------------------------------------------------------
# 5. GUARDAR EN GOOGLE DRIVE
# ---------------------------------------------------------
# Ruta de salida
ruta_salida = '/content/drive/My Drive/padron_procesado_final.csv'

print(f"Guardando archivo en: {ruta_salida}")
df_final.to_csv(ruta_salida, index=False)

print("¡LISTO! El archivo se guardó correctamente en tu Google Drive.")
print("Puedes buscarlo en tu carpeta 'Mi Unidad' con el nombre 'padron_procesado_final.csv'")
